# Admin Module - API Routes
# CRUD operations for Skills, Templates, Resources with auto-sync to ChromaDB

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from modules.admin.api.schemas import (
    SkillNodeCreate, SkillNodeUpdate, SkillNodeResponse,
    SkillTreeTemplateCreate, SkillTreeTemplateResponse,
    LearningResourceCreate, LearningResourceResponse,
    SuccessResponse, ErrorResponse
)
from modules.admin.providers import get_skill_service, get_sync_service

router = APIRouter(prefix="/admin", tags=["Admin"])


# ============================================================
# SKILL TREE TEMPLATE ENDPOINTS
# ============================================================

@router.get(
    "/templates",
    response_model=List[SkillTreeTemplateResponse],
    summary="Lấy danh sách Skill Tree Templates"
)
async def list_templates(skill_service = Depends(get_skill_service)):
    """Lấy danh sách tất cả skill tree templates"""
    templates = await skill_service.get_all_templates()
    return templates


@router.post(
    "/templates",
    response_model=SkillTreeTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo Skill Tree Template mới"
)
async def create_template(
    data: SkillTreeTemplateCreate,
    skill_service = Depends(get_skill_service)
):
    """Tạo skill tree template mới"""
    template = await skill_service.create_template(data.dict())
    return template


@router.get(
    "/templates/{template_id}",
    response_model=SkillTreeTemplateResponse,
    summary="Lấy chi tiết Template"
)
async def get_template(
    template_id: str,
    skill_service = Depends(get_skill_service)
):
    """Lấy chi tiết một template theo ID"""
    template = await skill_service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.delete(
    "/templates/{template_id}",
    response_model=SuccessResponse,
    summary="Xóa Template"
)
async def delete_template(
    template_id: str,
    skill_service = Depends(get_skill_service)
):
    """Xóa template và tất cả nodes bên trong"""
    await skill_service.delete_template(template_id)
    return SuccessResponse(message=f"Template {template_id} deleted")


# ============================================================
# SKILL NODE ENDPOINTS
# ============================================================

@router.get(
    "/templates/{template_id}/nodes",
    response_model=List[SkillNodeResponse],
    summary="Lấy tất cả nodes trong template"
)
async def list_nodes(
    template_id: str,
    skill_service = Depends(get_skill_service)
):
    """Lấy tất cả skill nodes trong một template"""
    nodes = await skill_service.get_template_nodes(template_id)
    return nodes


@router.post(
    "/nodes",
    response_model=SkillNodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo Skill Node mới"
)
async def create_node(
    data: SkillNodeCreate,
    skill_service = Depends(get_skill_service),
    sync_service = Depends(get_sync_service)
):
    """Tạo skill node mới và sync vào ChromaDB"""
    node = await skill_service.create_node(data.dict())
    sync_service.sync_skill_node(node)
    return node


@router.get(
    "/nodes/{node_id}",
    response_model=SkillNodeResponse,
    summary="Lấy chi tiết Node"
)
async def get_node(
    node_id: str,
    skill_service = Depends(get_skill_service)
):
    """Lấy chi tiết một skill node"""
    node = await skill_service.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.put(
    "/nodes/{node_id}",
    response_model=SkillNodeResponse,
    summary="Cập nhật Skill Node"
)
async def update_node(
    node_id: str,
    data: SkillNodeUpdate,
    skill_service = Depends(get_skill_service),
    sync_service = Depends(get_sync_service)
):
    """Cập nhật skill node và re-sync ChromaDB"""
    node = await skill_service.update_node(node_id, data.dict(exclude_unset=True))
    sync_service.sync_skill_node(node)
    return node


@router.delete(
    "/nodes/{node_id}",
    response_model=SuccessResponse,
    summary="Xóa Skill Node"
)
async def delete_node(
    node_id: str,
    skill_service = Depends(get_skill_service),
    sync_service = Depends(get_sync_service)
):
    """Xóa skill node khỏi PostgreSQL và ChromaDB"""
    await skill_service.delete_node(node_id)
    sync_service.delete_skill_from_vector(node_id)
    return SuccessResponse(message=f"Node {node_id} deleted")


@router.get(
    "/nodes/{node_id}/children",
    response_model=List[SkillNodeResponse],
    summary="Lấy các node con"
)
async def get_node_children(
    node_id: str,
    skill_service = Depends(get_skill_service)
):
    """Lấy tất cả node con trực tiếp của một node"""
    children = await skill_service.get_node_children(node_id)
    return children


# ============================================================
# LEARNING RESOURCE ENDPOINTS
# ============================================================

@router.post(
    "/resources",
    response_model=LearningResourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm Learning Resource"
)
async def create_resource(
    data: LearningResourceCreate,
    skill_service = Depends(get_skill_service),
    sync_service = Depends(get_sync_service)
):
    """Thêm tài liệu học tập cho một skill node"""
    resource = await skill_service.create_resource(data.dict())
    sync_service.sync_resource(resource)
    return resource


@router.get(
    "/nodes/{node_id}/resources",
    response_model=List[LearningResourceResponse],
    summary="Lấy resources của node"
)
async def get_node_resources(
    node_id: str,
    skill_service = Depends(get_skill_service)
):
    """Lấy tất cả learning resources của một skill node"""
    resources = await skill_service.get_node_resources(node_id)
    return resources


@router.delete(
    "/resources/{resource_id}",
    response_model=SuccessResponse,
    summary="Xóa Resource"
)
async def delete_resource(
    resource_id: str,
    skill_service = Depends(get_skill_service),
    sync_service = Depends(get_sync_service)
):
    """Xóa learning resource"""
    await skill_service.delete_resource(resource_id)
    sync_service.delete_skill_from_vector(resource_id)
    return SuccessResponse(message=f"Resource {resource_id} deleted")


# ============================================================
# SYNC ENDPOINTS
# ============================================================

@router.post(
    "/sync/rebuild",
    response_model=SuccessResponse,
    summary="Rebuild ChromaDB Index"
)
async def rebuild_index(
    skill_service = Depends(get_skill_service),
    sync_service = Depends(get_sync_service)
):
    """Rebuild toàn bộ ChromaDB index từ PostgreSQL"""
    all_skills = await skill_service.get_all_skills()
    count = sync_service.rebuild_index(all_skills)
    return SuccessResponse(
        message=f"Rebuilt index with {count} skills",
        data={"synced_count": count}
    )
