from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.economy import Transaction, TransactionType, Wallet
from app.models.match import Match, MatchStatus
from app.models.rating import PlayerRating
from app.models.social import Post
from app.models.tournament import Tournament, TournamentParticipant, TournamentStatus
from app.models.trust import PlayerTrust
from app.models.user import User


async def get_platform_analytics(db: AsyncSession) -> dict:
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total_tournaments = (await db.execute(select(func.count()).select_from(Tournament))).scalar_one()
    total_tournaments_completed = (
        await db.execute(
            select(func.count()).select_from(Tournament).where(Tournament.status == TournamentStatus.COMPLETED)
        )
    ).scalar_one()
    total_matches = (await db.execute(select(func.count()).select_from(Match))).scalar_one()
    total_matches_completed = (
        await db.execute(select(func.count()).select_from(Match).where(Match.status == MatchStatus.COMPLETED))
    ).scalar_one()
    total_disputes = (
        await db.execute(select(func.count()).select_from(Match).where(Match.disputed_by.isnot(None)))
    ).scalar_one()
    total_wallet_balance = (await db.execute(select(func.coalesce(func.sum(Wallet.balance), 0)))).scalar_one()
    total_prize_distributed = (
        await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.type == TransactionType.PRIZE_PAYOUT
            )
        )
    ).scalar_one()
    total_posts = (await db.execute(select(func.count()).select_from(Post))).scalar_one()

    return {
        "total_users": total_users,
        "total_tournaments": total_tournaments,
        "total_tournaments_completed": total_tournaments_completed,
        "total_matches": total_matches,
        "total_matches_completed": total_matches_completed,
        "total_disputes": total_disputes,
        "total_wallet_balance": total_wallet_balance,
        "total_prize_distributed": total_prize_distributed,
        "total_posts": total_posts,
    }


async def get_player_analytics(db: AsyncSession, user_id: UUID) -> dict | None:
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        return None

    rating_result = await db.execute(select(PlayerRating).where(PlayerRating.user_id == user_id))
    rating = rating_result.scalar_one_or_none()

    trust_result = await db.execute(select(PlayerTrust).where(PlayerTrust.user_id == user_id))
    trust = trust_result.scalar_one_or_none()

    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    wallet = wallet_result.scalar_one_or_none()

    matches_result = await db.execute(
        select(Match).where(
            Match.status == MatchStatus.COMPLETED,
            (Match.player_a_id == user_id) | (Match.player_b_id == user_id),
        )
    )
    matches = matches_result.scalars().all()

    total_scored = 0
    total_conceded = 0
    for m in matches:
        if m.player_a_id == user_id:
            total_scored += m.score_a or 0
            total_conceded += m.score_b or 0
        else:
            total_scored += m.score_b or 0
            total_conceded += m.score_a or 0

    played = len(matches)
    wins = rating.wins if rating else 0
    losses = rating.losses if rating else 0

    # Accurate regardless of prize amount — reads the tournament's own
    # winner_id, set at the moment it was actually completed (works for
    # free tournaments too, not just ones with a distributed prize).
    tournaments_won_result = await db.execute(
        select(func.count()).select_from(Tournament).where(
            Tournament.winner_id == user_id, Tournament.status == TournamentStatus.COMPLETED
        )
    )
    tournaments_won = tournaments_won_result.scalar_one()

    return {
        "user_id": user_id,
        "display_name": user.display_name,
        "rating": rating.rating if rating else 1000,
        "matches_played": played,
        "wins": wins,
        "losses": losses,
        "win_rate": round((wins / played) * 100, 1) if played > 0 else 0.0,
        "avg_goals_scored": round(total_scored / played, 2) if played > 0 else 0.0,
        "avg_goals_conceded": round(total_conceded / played, 2) if played > 0 else 0.0,
        "trust_score": trust.trust_score if trust else 100,
        "wallet_balance": wallet.balance if wallet else 0,
        "tournaments_won": tournaments_won,
    }


async def get_tournament_analytics(db: AsyncSession, tournament_id: UUID) -> dict | None:
    tournament_result = await db.execute(select(Tournament).where(Tournament.id == tournament_id))
    tournament = tournament_result.scalar_one_or_none()
    if tournament is None:
        return None

    participant_count_result = await db.execute(
        select(func.count()).select_from(TournamentParticipant).where(
            TournamentParticipant.tournament_id == tournament_id
        )
    )
    participant_count = participant_count_result.scalar_one()

    matches_result = await db.execute(select(Match).where(Match.tournament_id == tournament_id))
    matches = matches_result.scalars().all()
    matches_total = len(matches)
    completed = [m for m in matches if m.status == MatchStatus.COMPLETED]
    matches_completed = len(completed)

    total_goals = sum((m.score_a or 0) + (m.score_b or 0) for m in completed)
    avg_goals = round(total_goals / matches_completed, 2) if matches_completed > 0 else 0.0

    return {
        "tournament_id": tournament_id,
        "name": tournament.name,
        "format": tournament.format,
        "participant_count": participant_count,
        "matches_total": matches_total,
        "matches_completed": matches_completed,
        "avg_goals_per_match": avg_goals,
        "entry_fee": tournament.entry_fee,
        "prize_pool": tournament.prize_pool,
        "prize_distributed": tournament.prize_distributed,
    }
