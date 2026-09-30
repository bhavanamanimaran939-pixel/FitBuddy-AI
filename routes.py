from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Form
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request

from fastapi.responses import HTMLResponse

from fastapi.templating import Jinja2Templates

from pydantic import ValidationError

from sqlalchemy import select

from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db

from .gemini_flash_generator import (
    generate_nutrition_tip_with_flash
)

from .gemini_generator import (
    generate_workout_gemini
)

from .models import Plan
from .models import User

from .schemas import FeedbackRequest
from .schemas import UserInput

from .updated_plan import update_workout_plan


router = APIRouter()


templates = Jinja2Templates(
    directory="templates"
)


def error_response(
    request: Request,
    message: str,
    status_code: int = 400
):

    return templates.TemplateResponse(

        request=request,

        name="error.html",

        context={
            "message": message
        },

        status_code=status_code
    )


def get_user_and_plan(
    db: Session,
    user_id: str
):

    user = db.scalar(

        select(User).where(
            User.user_id == user_id
        )
    )

    plan = db.scalar(

        select(Plan)
        .where(Plan.user_id == user_id)
        .order_by(Plan.id.desc())
    )

    return user, plan


@router.get(
    "/",
    response_class=HTMLResponse
)
def home(request: Request):

    return templates.TemplateResponse(

        request=request,

        name="index.html"
    )


@router.post(
    "/generate-workout",
    response_class=HTMLResponse
)
def generate_workout(

    request: Request,

    name: str = Form(...),

    user_id: str = Form(...),

    age: int = Form(...),

    weight: float = Form(...),

    goal: str = Form(...),

    intensity: str = Form(...),

    db: Session = Depends(get_db)
):

    try:

        user_input = UserInput(

            name=name,

            user_id=user_id,

            age=age,

            weight=weight,

            goal=goal,

            intensity=intensity
        )

    except ValidationError as exc:

        message = "; ".join(
            err["msg"]
            for err in exc.errors()
        )

        return error_response(
            request,
            message
        )


    existing_user = db.scalar(

        select(User).where(
            User.user_id == user_input.user_id
        )
    )


    if existing_user:

        existing_user.name = user_input.name
        existing_user.age = user_input.age
        existing_user.weight = user_input.weight
        existing_user.goal = user_input.goal
        existing_user.intensity = user_input.intensity

        user = existing_user

        old_plans = db.scalars(

            select(Plan)
            .where(
                Plan.user_id == user_input.user_id
            )

        ).all()

        for old_plan in old_plans:

            db.delete(old_plan)

    else:

        user = User(
            **user_input.model_dump()
        )

        db.add(user)


    try:

        workout_plan = generate_workout_gemini(
            user_input
        )

        nutrition_tip = generate_nutrition_tip_with_flash(
            user_input.goal
        )

    except Exception as exc:

        db.rollback()

        return error_response(

            request,

            f"AI generation failed: {exc}",

            502
        )


    db.add(

        Plan(

            user_id=user_input.user_id,

            original_plan=workout_plan,

            nutrition_tip=nutrition_tip
        )
    )


    db.commit()


    plan = db.scalar(

        select(Plan)
        .where(
            Plan.user_id == user_input.user_id
        )
        .order_by(Plan.id.desc())
    )


    return templates.TemplateResponse(

        request=request,

        name="result.html",

        context={

            "user": user,

            "plan": plan,

            "message":
                "Your 7-day plan was generated successfully."
        }
    )


@router.post(
    "/submit-feedback",
    response_class=HTMLResponse
)
def submit_feedback(

    request: Request,

    user_id: str = Form(...),

    feedback: str = Form(...),

    db: Session = Depends(get_db)
):

    try:

        request_data = FeedbackRequest(

            user_id=user_id,

            feedback=feedback
        )

    except ValidationError as exc:

        return error_response(

            request,

            "; ".join(
                err["msg"]
                for err in exc.errors()
            )
        )


    user, plan = get_user_and_plan(

        db,

        request_data.user_id
    )


    if not user or not plan:

        return error_response(

            request,

            "User ID not found. Generate a plan first.",

            404
        )


    try:

        revised = update_workout_plan(

            plan.original_plan,

            request_data.feedback,

            user.goal,

            user.intensity
        )


        new_tip = generate_nutrition_tip_with_flash(

            user.goal
        )


    except Exception as exc:

        return error_response(

            request,

            f"AI update failed: {exc}",

            502
        )


    plan.updated_plan = revised

    plan.updated_nutrition_tip = new_tip

    plan.feedback = request_data.feedback

    plan.updated_at = datetime.now(
        timezone.utc
    )


    db.commit()

    db.refresh(plan)


    return templates.TemplateResponse(

        request=request,

        name="result.html",

        context={

            "user": user,

            "plan": plan,

            "message":
                "Your plan was updated using your feedback."
        }
    )


@router.get(
    "/view-all-users",
    response_class=HTMLResponse
)
def view_all_users(

    request: Request,

    key: str = Query(default=""),

    db: Session = Depends(get_db)
):

    settings = get_settings()


    if key != settings.admin_key:

        return error_response(

            request,

            "Admin access denied. "
            "Provide the correct admin key in the URL.",

            403
        )


    users = db.scalars(

        select(User)
        .order_by(User.created_at.desc())

    ).all()


    plans = {

        p.user_id: p

        for p in db.scalars(

            select(Plan)
            .order_by(Plan.id.desc())

        ).all()
    }


    return templates.TemplateResponse(

        request=request,

        name="all_users.html",

        context={

            "users": users,

            "plans": plans,

            "admin_key": key
        }
    )


@router.get("/api/health")
def health():

    return {

        "status": "ok",

        "service": "FitBuddy"
    }


@router.post("/api/generate-workout")
def api_generate(

    payload: UserInput,

    db: Session = Depends(get_db)
):

    existing = db.scalar(

        select(User).where(
            User.user_id == payload.user_id
        )
    )


    if existing:

        user = existing

        user.name = payload.name
        user.age = payload.age
        user.weight = payload.weight
        user.goal = payload.goal
        user.intensity = payload.intensity


        old_plans = db.scalars(

            select(Plan)
            .where(
                Plan.user_id == payload.user_id
            )

        ).all()


        for old_plan in old_plans:

            db.delete(old_plan)

    else:

        user = User(
            **payload.model_dump()
        )

        db.add(user)


    try:

        workout = generate_workout_gemini(
            payload
        )

        tip = generate_nutrition_tip_with_flash(
            payload.goal
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(

            status_code=502,

            detail=f"AI generation failed: {exc}"
        )


    db.add(

        Plan(

            user_id=payload.user_id,

            original_plan=workout,

            nutrition_tip=tip
        )
    )


    db.commit()


    return {

        "user_id":
            payload.user_id,

        "message":
            "Plan generated",

        "workout_plan":
            workout,

        "nutrition_tip":
            tip
    }


@router.post("/api/submit-feedback")
def api_feedback(

    payload: FeedbackRequest,

    db: Session = Depends(get_db)
):

    user, plan = get_user_and_plan(

        db,

        payload.user_id
    )


    if not user or not plan:

        raise HTTPException(

            status_code=404,

            detail="User ID not found"
        )


    try:

        revised = update_workout_plan(

            plan.original_plan,

            payload.feedback,

            user.goal,

            user.intensity
        )


        tip = generate_nutrition_tip_with_flash(
            user.goal
        )

    except Exception as exc:

        raise HTTPException(

            status_code=502,

            detail=f"AI update failed: {exc}"
        )


    plan.updated_plan = revised

    plan.updated_nutrition_tip = tip

    plan.feedback = payload.feedback

    plan.updated_at = datetime.now(
        timezone.utc
    )


    db.commit()


    return {

        "user_id":
            payload.user_id,

        "message":
            "Plan updated",

        "updated_plan":
            revised,

        "nutrition_tip":
            tip
    }


@router.get("/api/users")
def api_users(

    key: str = Query(default=""),

    db: Session = Depends(get_db)
):

    settings = get_settings()


    if key != settings.admin_key:

        raise HTTPException(

            status_code=403,

            detail="Invalid admin key"
        )


    users = db.scalars(

        select(User)
        .order_by(User.created_at.desc())

    ).all()


    return [

        {

            "user_id":
                u.user_id,

            "name":
                u.name,

            "age":
                u.age,

            "weight":
                u.weight,

            "goal":
                u.goal,

            "intensity":
                u.intensity,

            "created_at":
                u.created_at
        }

        for u in users
    ]