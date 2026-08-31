from fastapi import APIRouter

from app.api.v1 import auth, fraud, matches, posts, ratings, social, tournaments, trust, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(social.router, prefix="/users", tags=["social"])
api_router.include_router(tournaments.router, prefix="/tournaments", tags=["tournaments"])
api_router.include_router(matches.router, prefix="/matches", tags=["matches"])
api_router.include_router(
    matches.tournament_matches_router, prefix="/tournaments", tags=["matches"]
)
api_router.include_router(ratings.router, prefix="/ratings", tags=["ratings"])
api_router.include_router(trust.router, prefix="/trust", tags=["trust"])
api_router.include_router(fraud.router, prefix="/fraud", tags=["fraud"])
api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
