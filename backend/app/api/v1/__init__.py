from fastapi import APIRouter

from app.api.v1 import auth, matches, ratings, tournaments, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(tournaments.router, prefix="/tournaments", tags=["tournaments"])
api_router.include_router(matches.router, prefix="/matches", tags=["matches"])
api_router.include_router(
    matches.tournament_matches_router, prefix="/tournaments", tags=["matches"]
)
api_router.include_router(ratings.router, prefix="/ratings", tags=["ratings"])
