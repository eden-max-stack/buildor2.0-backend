import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import json
import random
import pickle
import os

from core_engine.models.gnn_models import HintGeneratorGNN, NUM_EDIT_TYPES

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

# Edit-type token sets (derived from mutation metadata)
_OPERATORS   = {'+', '-', '*', '/', '%', '**', '//', '&', '|', '^', '<<', '>>'}
_COMPARISONS = {'==', '!=', '<', '>', '<=', '>='}
_LOGICALS    = {'and', 'or', 'not'}
_BOOLEANS    = {'True', 'False'}
EDIT_TYPE_LABELS = [
    'none', 'replace_operator', 'replace_comparison',
    'replace_logical', 'replace_boolean', 'replace_constant',
]


def log_print(message):
    print(message)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(message + '\n')


def get_edit_type(meta):
    """Derive edit-type index from mutation metadata."""
    if meta is None:
        return 0
    orig = str(meta.get('original_token', ''))
    if orig in _OPERATORS:
        return 1
    if orig in _COMPARISONS:
        return 2
    if orig in _LOGICALS:
        return 3
    if orig in _BOOLEANS:
        return 4
    return 5  # replace_constant (integers, floats, etc.)


class FocalLoss(nn.Module):
    """Focal loss for imbalanced node-level localization."""
    def __init__(self, alpha=0.25, gamma=2.0, pos_weight=None):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.pos_weight = pos_weight

    def forward(self, logits, targets):
        bce = F.binary_cross_entropy_with_logits(
            logits, targets, pos_weight=self.pos_weight, reduction='none'
        )
        p_t = torch.sigmoid(logits) * targets + (1 - torch.sigmoid(logits)) * (1 - targets)
        alpha_t = self.alpha * targets + (1 - self.alpha) * (1 - targets)
        return (alpha_t * (1 - p_t) ** self.gamma * bce).mean()


def get_loss_weights(epoch):
    """Curriculum loss weights: early=cls/loc focus, mid=loc/patch, late=loc/patch dominant."""
    if epoch < 50:
        return 0.7, 1.5, 0.5, 0.3   # cls, loc, patch, edit
    if epoch < 100:
        return 0.5, 1.5, 1.5, 0.5
    return 0.3, 1.7, 2.3, 0.1       # edit is at ceiling — push loc/patch


def compute_class_weights(samples, num_classes, device):
    """Inverse-frequency class weights derived from dataset counts."""
    counts = torch.zeros(num_classes)
    for s in samples:
        counts[s['target_cls']] += 1
    total = counts.sum()
    weights = total / (num_classes * counts.clamp(min=1))
    return weights.to(device)


def process_cached_sample(sample, model, device, criterion_cls, criterion_loc,
                          criterion_patch, criterion_edit, vocab, epoch):
    """Process one pre-cached sample.
    Returns (loss, cls_ok, loc_ok, loc3_ok, mrr_contrib,
             patch_ok, patch3_ok, pred_patch_ok, edit_ok, is_buggy, had_target).
    """
    t_user = sample['t_user'].to(device)
    t_opt  = sample['t_opt'].to(device)
    target_cls = sample['target_cls']
    is_buggy   = sample['is_buggy']

    cls_out, loc_out, patch_out, edit_out = model(t_user, t_opt)

    loss_cls = criterion_cls(cls_out.unsqueeze(0), torch.tensor([target_cls], device=device))

    num_nodes  = t_user.x.shape[0]
    target_loc = torch.zeros((num_nodes, 1), device=device)
    loss_patch = torch.tensor(0.0, device=device)

    meta      = sample.get('metadata')
    edit_type = get_edit_type(meta) if is_buggy else 0
    loss_edit = criterion_edit(edit_out.unsqueeze(0), torch.tensor([edit_type], device=device))
    edit_ok   = (torch.argmax(edit_out).item() == edit_type)

    loc_hit = loc_topk_hit = patch_hit = patch3_hit = pred_patch_ok = False
    mrr_contrib = 0.0
    had_target  = False

    if is_buggy and sample.get('bug_line_indices'):
        bug_line_indices = sample['bug_line_indices']
        had_target = True

        for bi in bug_line_indices:
            if bi < num_nodes:
                target_loc[bi] = 1.0

        orig_token      = str(meta['original_token'])
        target_token_id = vocab.get(orig_token, 0)

        patch_losses = []
        for bi in bug_line_indices:
            if bi < num_nodes:
                patch_losses.append(
                    criterion_patch(
                        patch_out[bi].unsqueeze(0),
                        torch.tensor([target_token_id], device=device),
                    )
                )
        if patch_losses:
            loss_patch = sum(patch_losses) / len(patch_losses)

        # --- Localization: Top-1, Top-3, MRR ---
        loc_scores   = loc_out.squeeze(-1)
        pred_bug_idx = torch.argmax(loc_scores).item()
        loc_hit      = (pred_bug_idx in bug_line_indices)

        k        = min(3, num_nodes)
        topk_idx = torch.topk(loc_scores, k).indices.tolist()
        loc_topk_hit = any(bi in topk_idx for bi in bug_line_indices)

        ranks = torch.argsort(loc_scores, descending=True).tolist()
        for rank, idx in enumerate(ranks):
            if idx in bug_line_indices:
                mrr_contrib = 1.0 / (rank + 1)
                break

        valid_indices = [bi for bi in bug_line_indices if bi < num_nodes]
        if valid_indices:
            pk = min(3, NUM_PATCH_CLASSES)
            # Oracle patch@1: any gold node correct
            patch_hit  = any(
                torch.argmax(patch_out[bi]).item() == target_token_id
                for bi in valid_indices
            )
            # Oracle patch@3: any gold node in top-3 predictions
            patch3_hit = any(
                target_token_id in torch.topk(patch_out[bi], pk).indices.tolist()
                for bi in valid_indices
            )
            # True inference patch: predicted localization node
            pred_patch_token = torch.argmax(patch_out[pred_bug_idx]).item()
            pred_patch_ok    = (pred_patch_token == target_token_id)

    loss_loc = criterion_loc(loc_out, target_loc)
    w_cls, w_loc, w_patch, w_edit = get_loss_weights(epoch)
    loss = w_cls * loss_cls + w_loc * loss_loc + w_patch * loss_patch + w_edit * loss_edit

    cls_ok = (torch.argmax(cls_out).item() == target_cls)
    return (loss, cls_ok, loc_hit, loc_topk_hit, mrr_contrib,
            patch_hit, patch3_hit, pred_patch_ok, edit_ok, is_buggy, had_target)


def train():
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write("--- MBPP Training (Enhanced: JK-GNN, FocalLoss, EditType, DynWeights) ---\n")

    log_print("--- Starting Enhanced MBPP Training ---")

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
        log_print(f"GPU : {torch.cuda.get_device_name(0)}")
        log_print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        log_print(f"Device: {device}")
    else:
        log_print(f"Device: {device} (no GPU detected — training on CPU)")

    num_classes = len(bug_types)
    model = HintGeneratorGNN(
        MAX_VOCAB_SIZE,
        EMBED_DIM,
        128,
        num_classes,
        num_patch_classes=NUM_PATCH_CLASSES,
        num_edit_types=NUM_EDIT_TYPES,
    ).to(device)

    ckpt_path = 'gnn_model_mbpp_best_new.pth'
    if os.path.exists(ckpt_path):
        try:
            model.load_state_dict(torch.load(ckpt_path, map_location=device), strict=False)
            log_print(f"Warm-started (partial) from {ckpt_path}")
        except Exception as e:
            log_print(f"Checkpoint skipped (architecture changed): {e}")

    optimizer = optim.Adam(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=0.5, min_lr=1e-5)

    class_weights = compute_class_weights(train_samples, num_classes, device)
    log_print(f"Class weights (freq-derived): {[round(w, 3) for w in class_weights.tolist()]}")
    criterion_cls   = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.05)
    criterion_loc   = FocalLoss(alpha=0.25, gamma=2.0, pos_weight=torch.tensor([10.0], device=device))
    criterion_patch = nn.CrossEntropyLoss(label_smoothing=0.05)
    criterion_edit  = nn.CrossEntropyLoss()

    best_val_e2e = 0.0

    for epoch in range(EPOCHS):
        model.train()
        t_loss     = 0.0
        t_cls      = t_loc = t_loc3 = t_patch = t_patch3 = t_edit = t_loc_att = 0
        t_mrr_sum  = 0.0
        t_processed = t_errors = 0

        random.shuffle(train_samples)

        optimizer.zero_grad()
        for i, sample in enumerate(train_samples):
            try:
                (loss, cls_ok, loc_ok, loc3_ok, mrr_c,
                 patch_ok, patch3_ok, pred_p_ok, edit_ok, is_buggy, had_target) = \
                    process_cached_sample(
                        sample, model, device,
                        criterion_cls, criterion_loc,
                        criterion_patch, criterion_edit,
                        vocab, epoch,
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
                if edit_ok:
                    t_edit += 1
                if is_buggy and had_target:
                    t_loc_att  += 1
                    t_mrr_sum  += mrr_c
                    if loc_ok:    t_loc    += 1
                    if loc3_ok:   t_loc3   += 1
                    if patch_ok:  t_patch  += 1
                    if patch3_ok: t_patch3 += 1

            except Exception as e:
                t_errors += 1
                if t_errors <= 3:
                    log_print(f"  [ERR] train {i}: {e}")
                continue

        # Flush any remaining accumulated gradients at end of epoch
        if t_processed % ACCUM_STEPS != 0:
            nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
            optimizer.step()
            optimizer.zero_grad()

        if t_processed > 0:
            cls_a  = t_cls  / t_processed * 100
            edit_a = t_edit / t_processed * 100
            loc_a  = (t_loc    / t_loc_att * 100)  if t_loc_att else 0
            loc3_a = (t_loc3   / t_loc_att * 100)  if t_loc_att else 0
            mrr_a  = (t_mrr_sum / t_loc_att)        if t_loc_att else 0
            pat_a  = (t_patch  / t_loc_att * 100)  if t_loc_att else 0
            pat3_a = (t_patch3 / t_loc_att * 100)  if t_loc_att else 0
            log_print(
                f"Ep {epoch+1}/{EPOCHS} [Tr] L={t_loss/t_processed:.3f} "
                f"Cls={cls_a:.1f}% Edit={edit_a:.1f}% "
                f"Loc@1={loc_a:.1f}% Loc@3={loc3_a:.1f}% MRR={mrr_a:.3f} "
                f"Pat@1={pat_a:.1f}% Pat@3={pat3_a:.1f}% "
                f"n={t_processed} err={t_errors}"
            )

        model.eval()
        v_cls = v_loc = v_loc3 = v_patch = v_patch3 = v_edit = v_loc_att = 0
        v_e2e_strict = v_e2e_relaxed = v_e2e_pred = 0
        v_mrr_sum = 0.0
        v_processed = 0

        with torch.no_grad():
            for sample in val_samples:
                try:
                    (_, cls_ok, loc_ok, loc3_ok, mrr_c,
                     patch_ok, patch3_ok, pred_p_ok, edit_ok, is_buggy, had_target) = \
                        process_cached_sample(
                            sample, model, device,
                            criterion_cls, criterion_loc,
                            criterion_patch, criterion_edit,
                            vocab, epoch,
                        )
                    v_processed += 1
                    if cls_ok:  v_cls  += 1
                    if edit_ok: v_edit += 1

                    if is_buggy and had_target:
                        v_loc_att  += 1
                        v_mrr_sum  += mrr_c
                        if loc_ok:    v_loc    += 1
                        if loc3_ok:   v_loc3   += 1
                        if patch_ok:  v_patch  += 1
                        if patch3_ok: v_patch3 += 1
                        # Strict E2E: cls + loc@1 + oracle patch@1
                        if cls_ok and loc_ok and patch_ok:
                            v_e2e_strict += 1
                        # Relaxed E2E: cls + loc@3 + oracle patch@3
                        if cls_ok and loc3_ok and patch3_ok:
                            v_e2e_relaxed += 1
                        # Predicted E2E: cls + loc@1 + patch at predicted node
                        if cls_ok and loc_ok and pred_p_ok:
                            v_e2e_pred += 1
                    elif not is_buggy and cls_ok:
                        v_e2e_strict  += 1
                        v_e2e_relaxed += 1
                        v_e2e_pred    += 1
                except Exception:
                    continue

        if v_processed > 0:
            v_cls_a  = v_cls  / v_processed * 100
            v_edit_a = v_edit / v_processed * 100
            v_loc_a  = (v_loc    / v_loc_att * 100) if v_loc_att else 0
            v_loc3_a = (v_loc3   / v_loc_att * 100) if v_loc_att else 0
            v_mrr_a  = (v_mrr_sum / v_loc_att)       if v_loc_att else 0
            v_pat_a  = (v_patch  / v_loc_att * 100) if v_loc_att else 0
            v_pat3_a = (v_patch3 / v_loc_att * 100) if v_loc_att else 0
            v_e2e_s  = v_e2e_strict  / v_processed * 100
            v_e2e_r  = v_e2e_relaxed / v_processed * 100
            v_e2e_p  = v_e2e_pred    / v_processed * 100

            log_print(
                f"         [Va] Cls={v_cls_a:.1f}% Edit={v_edit_a:.1f}% "
                f"Loc@1={v_loc_a:.1f}% Loc@3={v_loc3_a:.1f}% MRR={v_mrr_a:.3f} "
                f"Pat@1={v_pat_a:.1f}% Pat@3={v_pat3_a:.1f}% "
                f"E2E_strict={v_e2e_s:.1f}% E2E_relaxed={v_e2e_r:.1f}% E2E_pred={v_e2e_p:.1f}% "
                f"(n={v_processed})"
            )

            scheduler.step(1.0 - v_e2e_r / 100)

            if v_e2e_r > best_val_e2e:
                best_val_e2e = v_e2e_r
                torch.save(model.state_dict(), ckpt_path)
                with open(VOCAB_FILE, 'w', encoding='utf-8') as f:
                    json.dump(vocab, f)
                log_print(f"         ** Best Relaxed-E2E={v_e2e_r:.1f}% — saved **")

        if (epoch + 1) % 20 == 0:
            torch.save(model.state_dict(), f"gnn_model_mbpp_ep_new{epoch+1}.pth")
            log_print("  Checkpoint saved.")

    log_print(f"\n--- Training Complete. Best Val E2E: {best_val_e2e:.1f}% ---")


if __name__ == '__main__':
    train()
