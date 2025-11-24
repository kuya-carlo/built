import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session
from starlette.responses import JSONResponse

from src.models import (
    ErrorResponse,
    MaterialResponse,
    Materials,
    Project,
    ProjectAttribute,
    ProjectResponse,
    SingleSuccessResponse,
    SuccessResponse,
    get_session,
)
from src.utils import create, delete, log, prep_create, read, update


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
                    "model": SingleSuccessResponse[ProjectResponse],
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
                session,
            )
            return self._parse_material(material, session)

        @self.post(
            "/",
            responses={
                200: {
                    "description": "Materials created",
                    "model": SingleSuccessResponse[ProjectResponse],
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
                new_material.material_id,
                session,
            )
            return self._parse_material(new_material, session)

        @self.patch(
            "/{material_id}",
            responses={
                200: {
                    "description": "Updated material successfully",
                    "model": SingleSuccessResponse[ProjectResponse],
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
                material_id,
                session,
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
                material_id,
                session,
            )
            return JSONResponse(
                status_code=200, content=SuccessResponse(result="ok").model_dump_json()
            )

    @staticmethod
    def _parse_material(
        material: Materials, session: Optional[Session] = None
    ) -> SingleSuccessResponse[MaterialResponse]:
        project_summary = None
        if session:
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
