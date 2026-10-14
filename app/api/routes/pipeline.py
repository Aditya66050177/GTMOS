from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from app.db.database import get_db
from app.models import Account, Score, Opportunity
from app.schemas.crm import PipelineResponse, PipelineStageGroup, PipelineStage

router = APIRouter(prefix="/pipeline", tags=["Pipeline & CRM"])

@router.get("", response_model=PipelineResponse)
def get_pipeline(db: Session = Depends(get_db)):
    accounts = db.query(Account).all()
    scores = db.query(Score).all()
    score_map = {s.account_id: s for s in scores}
    opps = db.query(Opportunity).all()
    opp_map = {o.account_id: o for o in opps}

    stage_groups: Dict[str, List[Dict[str, Any]]] = {
        stage.value: [] for stage in PipelineStage
    }

    for a in accounts:
        curr_stage = a.stage or PipelineStage.RESEARCH.value
        if curr_stage not in stage_groups:
            curr_stage = PipelineStage.RESEARCH.value

        sc = score_map.get(a.id)
        opp = opp_map.get(a.id)

        stage_groups[curr_stage].append({
            "id": a.id,
            "name": a.name,
            "domain": a.domain,
            "industry": a.industry,
            "employee_count": a.employee_count,
            "country": a.country,
            "tier": sc.tier if sc else "Low",
            "total_score": sc.total_score if sc else 0.0,
            "deal_value": opp.deal_value if opp else None,
            "probability": opp.probability if opp else None
        })

    response_stages = {}
    for stg_name, acc_list in stage_groups.items():
        response_stages[stg_name] = PipelineStageGroup(
            stage=stg_name,
            count=len(acc_list),
            accounts=acc_list
        )

    return PipelineResponse(
        total_accounts=len(accounts),
        stages=response_stages
    )
