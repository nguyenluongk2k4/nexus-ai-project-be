from modules.skill_tree.infrastructure.repository import get_skill_tree_repository
from modules.skill_tree.usecases.get_resources import GetNodeResourcesUseCase
from modules.skill_tree.usecases.get_tree import GetSessionSkillTreeUseCase


def get_node_resources_usecase():
    return GetNodeResourcesUseCase(get_skill_tree_repository())

def get_session_skill_tree_usecase():
    return GetSessionSkillTreeUseCase(get_skill_tree_repository())

from modules.skill_tree.usecases.update_progress import UpdateResourceProgressUseCase

def get_update_resource_progress_usecase():
    return UpdateResourceProgressUseCase(get_skill_tree_repository())
