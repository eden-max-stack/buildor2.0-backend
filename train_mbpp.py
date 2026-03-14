import torch
import torch.nn as nn
import torch.optim as optim
import json
import random
import pickle
import os

from core_engine.models.gnn_models import HintGeneratorGNN

# --- Config ---
CACHE_FILE = 'training_cache_mbpp.pkl'
LOG_FILE = 'train_output_mbpp.txt'
VOCAB_FILE = 'vocab_mbpp.json'
EPOCHS = 200
LR = 0.0005
EMBED_DIM = 64
MAX_VOCAB_SIZE = 500
GRAD_CLIP = 1.0
ACCUM_STEPS = 8
NUM_PATCH_CLASSES = 39  # Only mutation tokens (IDs 1-38) + UNK (0)


def log_print(message):
    print(message)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(message + '\n')


def process_cached_sample(sample, model, device, criterion_cls, criterion_loc, criterion_patch, vocab):
    """Process one pre-cached sample. Returns (loss, cls_ok, loc_ok, patch_ok, is_buggy, had_target)."""
    t_user = sample['t_user'].to(device)
    t_opt = sample['t_opt'].to(device)
    target_cls = sample['target_cls']
    is_buggy = sample['is_buggy']

    cls_out, loc_out, patch_out = model(t_user, t_opt)

    loss_cls = criterion_cls(cls_out.unsqueeze(0), torch.tensor([target_cls], device=device))

    num_nodes = t_user.x.shape[0]
    target_loc = torch.zeros((num_nodes, 1), device=device)
    loss_patch = torch.tensor(0.0, device=device)

    loc_hit = False
    patch_hit = False
    had_target = False

    if is_buggy and sample.get('bug_line_indices'):
        bug_line_indices = sample['bug_line_indices']
        had_target = True

        for bi in bug_line_indices:
            if bi < num_nodes:
                target_loc[bi] = 1.0

        meta = sample['metadata']
        orig_token = str(meta['original_token'])
        target_token_id = vocab.get(orig_token, 0)

        patch_losses = []
        for bi in bug_line_indices:
            if bi < num_nodes:
                pl = criterion_patch(
                    patch_out[bi].unsqueeze(0),
                    torch.tensor([target_token_id], device=device)
                )
                patch_losses.append(pl)

        if patch_losses:
            loss_patch = sum(patch_losses) / len(patch_losses)

        pred_bug_idx = torch.argmax(loc_out.squeeze(-1)).item()
        loc_hit = (pred_bug_idx in bug_line_indices)

        valid_indices = [bi for bi in bug_line_indices if bi < num_nodes]
        if valid_indices:
            pred_token = torch.argmax(patch_out[valid_indices[0]]).item()
            patch_hit = (pred_token == target_token_id)

    loss_loc = criterion_loc(loc_out, target_loc)
    loss = 0.5 * loss_cls + 1.0 * loss_loc + 1.0 * loss_patch

    cls_ok = (torch.argmax(cls_out).item() == target_cls)
    return loss, cls_ok, loc_hit, patch_hit, is_buggy, had_target


def train():
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write("--- MBPP Training (cached data + attention-cls) ---\n")

    log_print("--- Starting MBPP Training ---")

    with open(CACHE_FILE, 'rb') as f:
        cache = pickle.load(f)

    train_samples = cache['train']
    val_samples = cache['val']
    vocab = cache['vocab']
    bug_types = cache['bug_types']

    log_print(f"Loaded cache: Train={len(train_samples)}, Val={len(val_samples)}, Types={bug_types}")

    require_cuda = os.getenv('REQUIRE_CUDA', '0') not in ('0', 'false', 'False')
    if require_cuda and not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is not available, but REQUIRE_CUDA is enabled. "
            "Install a CUDA-enabled PyTorch build and ensure an NVIDIA GPU is accessible, "
            "or set REQUIRE_CUDA=0 to allow CPU training."
        )

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    if device.type == 'cuda':
        torch.backends.cudnn.benchmark = True
        log_print(f"Device: {device} ({torch.cuda.get_device_name(0)})")
    else:
        log_print(f"Device: {device}")

    model = HintGeneratorGNN(
        MAX_VOCAB_SIZE,
        EMBED_DIM,
        128,
        len(bug_types),
        num_patch_classes=NUM_PATCH_CLASSES,
    ).to(device)

    ckpt_path = 'gnn_model_mbpp_best.pth'
    if os.path.exists(ckpt_path):
        model.load_state_dict(torch.load(ckpt_path, map_location=device))
        log_print(f"Warm-started from {ckpt_path}")

    optimizer = optim.Adam(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=0.5, min_lr=1e-5)

    class_weights = torch.tensor([1.0, 5.0, 5.0]).to(device)
    criterion_cls = nn.CrossEntropyLoss(weight=class_weights)
    criterion_loc = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([10.0], device=device))
    criterion_patch = nn.CrossEntropyLoss()

    best_val_e2e = 0.0

    for epoch in range(EPOCHS):
        model.train()
        t_loss, t_cls, t_loc, t_patch, t_loc_att = 0.0, 0, 0, 0, 0
        t_processed, t_errors = 0, 0

        random.shuffle(train_samples)

        optimizer.zero_grad()
        for i, sample in enumerate(train_samples):
            try:
                loss, cls_ok, loc_ok, patch_ok, is_buggy, had_target = process_cached_sample(
                    sample,
                    model,
                    device,
                    criterion_cls,
                    criterion_loc,
                    criterion_patch,
                    vocab,
                )

                (loss / ACCUM_STEPS).backward()

                if (i + 1) % ACCUM_STEPS == 0:
                    nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
                    optimizer.step()
                    optimizer.zero_grad()

                t_processed += 1
                t_loss += loss.item()

                if cls_ok:
                    t_cls += 1

                if is_buggy and had_target:
                    t_loc_att += 1
                    if loc_ok:
                        t_loc += 1
                    if patch_ok:
                        t_patch += 1

            except Exception as e:
                t_errors += 1
                if t_errors <= 3:
                    log_print(f"  [ERR] train {i}: {e}")
                continue

        if t_processed > 0:
            cls_a = t_cls / t_processed * 100
            loc_a = (t_loc / t_loc_att * 100) if t_loc_att else 0
            pat_a = (t_patch / t_loc_att * 100) if t_loc_att else 0
            log_print(
                f"Ep {epoch+1}/{EPOCHS} [Tr] L={t_loss/t_processed:.3f} "
                f"Cls={cls_a:.1f}% Loc={loc_a:.1f}% Pat={pat_a:.1f}% "
                f"n={t_processed} err={t_errors}"
            )

        model.eval()
        v_cls, v_loc, v_patch, v_loc_att, v_e2e = 0, 0, 0, 0, 0
        v_processed = 0

        with torch.no_grad():
            for sample in val_samples:
                try:
                    _, cls_ok, loc_ok, patch_ok, is_buggy, had_target = process_cached_sample(
                        sample,
                        model,
                        device,
                        criterion_cls,
                        criterion_loc,
                        criterion_patch,
                        vocab,
                    )
                    v_processed += 1
                    if cls_ok:
                        v_cls += 1

                    if is_buggy and had_target:
                        v_loc_att += 1
                        if loc_ok:
                            v_loc += 1
                        if patch_ok:
                            v_patch += 1
                        if cls_ok and loc_ok and patch_ok:
                            v_e2e += 1
                    elif not is_buggy and cls_ok:
                        v_e2e += 1
                except Exception:
                    continue

        if v_processed > 0:
            v_cls_a = v_cls / v_processed * 100
            v_loc_a = (v_loc / v_loc_att * 100) if v_loc_att else 0
            v_pat_a = (v_patch / v_loc_att * 100) if v_loc_att else 0
            v_e2e_a = v_e2e / v_processed * 100

            log_print(
                f"         [Va] Cls={v_cls_a:.1f}% Loc={v_loc_a:.1f}% "
                f"Pat={v_pat_a:.1f}% E2E={v_e2e_a:.1f}% (n={v_processed})"
            )

            scheduler.step(1.0 - v_e2e_a / 100)

            if v_e2e_a > best_val_e2e:
                best_val_e2e = v_e2e_a
                torch.save(model.state_dict(), ckpt_path)
                with open(VOCAB_FILE, 'w', encoding='utf-8') as f:
                    json.dump(vocab, f)
                log_print(f"         ** Best E2E={v_e2e_a:.1f}% — saved **")

        if (epoch + 1) % 20 == 0:
            torch.save(model.state_dict(), f"gnn_model_mbpp_ep{epoch+1}.pth")
            log_print("  Checkpoint saved.")

    log_print(f"\n--- Training Complete. Best Val E2E: {best_val_e2e:.1f}% ---")


if __name__ == '__main__':
    train()
