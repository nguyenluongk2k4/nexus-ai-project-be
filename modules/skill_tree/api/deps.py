from modules.skill_tree.infrastructure.repository import get_skill_tree_repository
from modules.skill_tree.usecases.get_resources import GetNodeResourcesUseCase
from modules.skill_tree.usecases.get_tree import GetSessionSkillTreeUseCase
from modules.chat.infrastructure.repository import ChatRepositoryImpl


def get_node_resources_usecase():
    return GetNodeResourcesUseCase(get_skill_tree_repository())

def get_session_skill_tree_usecase():
    # Pass chat_repo so usecase can read generated tree from session context
    chat_repo = ChatRepositoryImpl()
    return GetSessionSkillTreeUseCase(get_skill_tree_repository(), chat_repo)

from modules.skill_tree.usecases.update_progress import UpdateResourceProgressUseCase

def get_update_resource_progress_usecase():
    return UpdateResourceProgressUseCase(get_skill_tree_repository())
