from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import (
    CandidateCluster,
    CandidateOrigin,
    DiscoveryRun,
    DiscoveryRunResult,
    ProductCandidate,
    SeedKeyword,
    SeedList,
)
from app.schemas.discovery import (
    CandidateClusterResponse,
    CandidateOriginResponse,
    DiscoveryRunCreate,
    DiscoveryRunResponse,
    DiscoveryRunResultResponse,
    SeedKeywordResponse,
    SeedListCreate,
    SeedListResponse,
)
from app.services.discovery_service import DiscoveryService

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.post("/seed-lists", response_model=SeedListResponse, status_code=201)
def create_seed_list(payload: SeedListCreate, db: Session = Depends(get_db)) -> SeedListResponse:
    try:
        seed_list = DiscoveryService(db).create_seed_list(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _seed_list_response(seed_list)


@router.get("/seed-lists", response_model=list[SeedListResponse])
def list_seed_lists(db: Session = Depends(get_db)) -> list[SeedListResponse]:
    return [_seed_list_response(row) for row in DiscoveryService(db).list_seed_lists()]


@router.post("/runs", response_model=DiscoveryRunResponse, status_code=201)
def create_discovery_run(
    payload: DiscoveryRunCreate,
    db: Session = Depends(get_db),
) -> DiscoveryRunResponse:
    try:
        run = DiscoveryService(db).run_discovery(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _run_response(db, run)


@router.get("/runs", response_model=list[DiscoveryRunResponse])
def list_discovery_runs(
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[DiscoveryRunResponse]:
    return [_run_response(db, run) for run in DiscoveryService(db).list_runs(limit=limit)]


@router.get("/runs/{run_id}", response_model=DiscoveryRunResponse)
def get_discovery_run(run_id: UUID, db: Session = Depends(get_db)) -> DiscoveryRunResponse:
    run = DiscoveryService(db).get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Discovery run not found")
    return _run_response(db, run)


def _seed_list_response(seed_list: SeedList) -> SeedListResponse:
    return SeedListResponse(
        id=str(seed_list.id),
        name=seed_list.name,
        description=seed_list.description,
        keywords=[_seed_keyword_response(keyword) for keyword in seed_list.keywords],
        metadata=seed_list.metadata_,
        created_at=seed_list.created_at,
        updated_at=seed_list.updated_at,
    )


def _seed_keyword_response(keyword: SeedKeyword) -> SeedKeywordResponse:
    return SeedKeywordResponse(
        id=str(keyword.id),
        seed_list_id=str(keyword.seed_list_id),
        keyword=keyword.keyword,
        category=keyword.category,
        status=keyword.status,
        metadata=keyword.metadata_,
    )


def _run_response(db: Session, run: DiscoveryRun) -> DiscoveryRunResponse:
    product_names = {
        str(product.id): product.canonical_name
        for product in db.query(ProductCandidate).all()
    }
    return DiscoveryRunResponse(
        id=str(run.id),
        seed_list_id=str(run.seed_list_id) if run.seed_list_id else None,
        status=run.status,
        source_plugins=run.source_plugins,
        parameters=run.parameters,
        summary=run.summary,
        error_message=run.error_message,
        started_at=run.started_at,
        finished_at=run.finished_at,
        clusters=[_cluster_response(row) for row in run.clusters],
        results=[_result_response(row, product_names) for row in run.results],
        origins=[_origin_response(row) for row in run.origins],
    )


def _cluster_response(cluster: CandidateCluster) -> CandidateClusterResponse:
    return CandidateClusterResponse(
        id=str(cluster.id),
        seed_keyword_id=str(cluster.seed_keyword_id) if cluster.seed_keyword_id else None,
        label=cluster.label,
        normalized_key=cluster.normalized_key,
        source_query=cluster.source_query,
        representative_title=cluster.representative_title,
        evidence_observation_ids=cluster.evidence_observation_ids,
        metadata=cluster.metadata_,
    )


def _result_response(
    result: DiscoveryRunResult,
    product_names: dict[str, str],
) -> DiscoveryRunResultResponse:
    product_id = str(result.product_id)
    return DiscoveryRunResultResponse(
        id=str(result.id),
        seed_keyword_id=str(result.seed_keyword_id) if result.seed_keyword_id else None,
        candidate_cluster_id=str(result.candidate_cluster_id),
        product_id=product_id,
        product_name=product_names.get(product_id, "unknown product"),
        status=result.status,
        rank_position=result.rank_position,
        opportunity_score=result.opportunity_score,
        recommendation=result.recommendation,
        metadata=result.metadata_,
    )


def _origin_response(origin: CandidateOrigin) -> CandidateOriginResponse:
    return CandidateOriginResponse(
        id=str(origin.id),
        product_id=str(origin.product_id),
        discovery_run_id=str(origin.discovery_run_id),
        seed_keyword_id=str(origin.seed_keyword_id) if origin.seed_keyword_id else None,
        candidate_cluster_id=str(origin.candidate_cluster_id)
        if origin.candidate_cluster_id
        else None,
        source_plugin=origin.source_plugin,
        source_query=origin.source_query,
        source_observation_id=str(origin.source_observation_id)
        if origin.source_observation_id
        else None,
        source_external_id=origin.source_external_id,
        title=origin.title,
        metadata=origin.metadata_,
    )
