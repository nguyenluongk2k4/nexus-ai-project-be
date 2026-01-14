# Admin Module - Database Models (Infrastructure Layer)
# Admin module imports models from their respective domain modules
# This file only contains admin-specific models (if any)

# Re-export skill tree models for backward compatibility
from modules.skill_tree.infrastructure.models import (
    SkillTreeTemplateModel,
    TemplateSkillNodeModel,
    TemplateSkillPathModel,
    LearningResourceModel
)

__all__ = [
    "SkillTreeTemplateModel",
    "TemplateSkillNodeModel", 
    "TemplateSkillPathModel",
    "LearningResourceModel"
]
