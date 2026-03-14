from .repository import UserRepository

class UserService:

    def __init__(self):
        self.repo = UserRepository()

    def create_user(self, user_data):
        return self.repo.create(user_data)

    def list_users(self):
        return self.repo.get_all()