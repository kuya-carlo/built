import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session
from starlette.responses import JSONResponse

from src.models import (
    ErrorResponse,
    GroupSuccessResponse,
    MaterialResponse,
    Materials,
    Project,
    ProjectAttribute,
    SingleSuccessResponse,
    SuccessResponse,
)
from src.models.response import MaterialSummary
from src.utils import create, delete, get_session, log, prep_create, read, update
from src.utils.helper import FilterMode, db_filter


class MaterialCreate(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "project_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Galvanized Square Steel",
                "qty_needed": 5,
                "qty_acquired": 2,
                "unit": "tona",
            }
        }
    }
    material_id: Optional[uuid.UUID] = None
    project_id: uuid.UUID
    name: str
    qty_needed: int
    qty_acquired: int
    unit: str


class MaterialUpdate(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "John",
                "qty_needed": 50,
                "qty_acquired": 30,
                "unit": "pcs",
            }
        }
    }
    project_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    qty_needed: Optional[int] = None
    qty_acquired: Optional[int] = None
    unit: Optional[str] = None


class MaterialRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/material", tags=["Materials"])
        self._register_routes()

    def _register_routes(self):
        @self.get(
            "/{material_id}",
            responses={
                200: {
                    "description": "Materials exists",
                    "model": SingleSuccessResponse[MaterialResponse],
                },
                404: {"description": "Materials not found", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def get_material(
            material_id: uuid.UUID, session: Session = Depends(get_session)
        ):
            material = read(session, material_id, Materials)
            log(
                "GET_MATERIAL",
                f"Got material info for {material_id}",
                session=session,
            )
            return self._parse_material(material, session)

        @self.post(
            "/",
            responses={
                200: {
                    "description": "Materials created",
                    "model": SingleSuccessResponse[MaterialResponse],
                },
                409: {"description": "Conflict", "model": ErrorResponse},
                422: {"description": "Validation Error", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def create_material(
            material_data: MaterialCreate,
            session: Session = Depends(get_session),
        ):
            material_dict = prep_create(material_data, "material_id")
            material = Materials.model_validate(material_dict)
            new_material = create(session, material)
            log(
                "CREATE_MATERIAL",
                f"Created material with id of {new_material.material_id}",
                session=session,
            )
            return self._parse_material(new_material, session)

        @self.patch(
            "/{material_id}",
            responses={
                200: {
                    "description": "Updated material successfully",
                    "model": SingleSuccessResponse[MaterialResponse],
                },
                422: {"description": "Validation Error", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def update_material(
            material_id: uuid.UUID,
            material_data: MaterialUpdate,
            session: Session = Depends(get_session),
        ):
            updated_material = update(session, material_id, material_data, Materials)
            log(
                "UPDATE_MATERIAL",
                f"Updated material with id {material_id}",
                session=session,
            )
            return self._parse_material(updated_material, session)

        @self.delete(
            "/{material_id}",
            responses={
                200: {
                    "description": "Materials deleted",
                    "model": SuccessResponse,
                },
                404: {"description": "Materials not found", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def delete_material(
            material_id: uuid.UUID,
            session: Session = Depends(get_session),
        ):
            delete(session, material_id, Materials)
            log(
                "DELETE_MATERIAL",
                f"Deleted material with id {material_id}",
                session=session,
            )
            return JSONResponse(
                status_code=200, content=SuccessResponse(result="ok").model_dump_json()
            )

        @self.get(
            "/",
            responses={
                200: {
                    "description": "Successfully got materials",
                    "model": GroupSuccessResponse[MaterialSummary],
                },
                404: {
                    "description": "Material for the project not found",
                    "model": ErrorResponse,
                },
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def list_materials(
            project_id: uuid.UUID,
            limit: int = 5,
            offset: int = 0,
            session: Session = Depends(get_session),
        ):
            materials = db_filter(
                session,
                Materials,
                project_id,
                Materials.project_id,
                Materials.name,
                FilterMode.ALL,
                limit,
                offset,
            )
            if not materials:
                log(
                    "LIST_MATERIALS",
                    f"Listed materials from project {project_id}",
                    code=404,
                    session=session,
                )
                raise ValueError(f"Materials with project id {project_id} not found")
            log(
                "LIST_PROJECT",
                f"Listed materials from project {project_id}",
                session=session,
            )
            return self._parse_materials(materials)

    @staticmethod
    def _parse_material(
        material: Materials, session: Optional[Session] = None, add_proj_summary=False
    ) -> SingleSuccessResponse[MaterialResponse]:
        project_summary = None
        if bool(session) and add_proj_summary:
            project_obj = read(session, material.project_id, Project)
            if project_obj:
                # Convert User to UserSummary
                project_summary = ProjectAttribute(
                    id=project_obj.project_id,
                    user_id=project_obj.user_id,
                    name=project_obj.name,
                    description=project_obj.description,
                    start_date=project_obj.start_date,
                    end_date=project_obj.end_date,
                    status=project_obj.status,
                    total_budget=project_obj.total_budget,
                )

        return SingleSuccessResponse[MaterialResponse](
            data=MaterialResponse(
                id=material.material_id,
                name=material.name,
                project_id=material.project_id,
                qty_needed=material.qty_needed,
                qty_acquired=material.qty_acquired,
                unit=material.unit,
                project=project_summary,
            )
        )

    @staticmethod
    def _parse_materials(
        materials: List[Materials],
    ) -> GroupSuccessResponse[MaterialSummary]:
        return GroupSuccessResponse(
            data=[
                MaterialSummary(
                    id=material.material_id,
                    name=material.name,
                    project_id=material.project_id,
                    qty_needed=material.qty_needed,
                    qty_acquired=material.qty_acquired,
                    unit=material.unit,
                )
                for material in materials
            ]
        )
