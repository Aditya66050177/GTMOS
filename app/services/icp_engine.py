from sqlalchemy.orm import Session
from app.models import Product, ICPProfile
from app.schemas.icp import ICPProfileSchema
from app.ai.llm import LLMService
from app.ai.prompts import GENERATE_ICP_PROMPT

class ICPEngine:
    def __init__(self, llm_service: LLMService = None):
        self.llm_service = llm_service or LLMService()

    def generate_icp_for_product(self, db: Session, product: Product) -> ICPProfile:
        """
        Generates an ICP profile for a product using LLMService,
        validates with ICPProfileSchema, and persists as structured columns.
        """
        prompt = GENERATE_ICP_PROMPT.format(
            name=product.name,
            description=product.description or "",
            target_market=product.target_market or [],
            geography=product.geography or [],
            price_range=product.price_range or ""
        )

        icp_schema_result: ICPProfileSchema = self.llm_service.generate_structured(
            prompt=prompt,
            schema=ICPProfileSchema
        )

        existing_profile = db.query(ICPProfile).filter_by(product_id=product.id).first()

        if existing_profile:
            existing_profile.industries = icp_schema_result.industries
            existing_profile.company_size_min = icp_schema_result.min_employees
            existing_profile.company_size_max = icp_schema_result.max_employees
            existing_profile.geographies = icp_schema_result.geographies
            existing_profile.buyer_roles = icp_schema_result.buyer_roles
            existing_profile.pain_points = icp_schema_result.pain_points
            existing_profile.technologies = icp_schema_result.technologies
            existing_profile.buying_triggers = icp_schema_result.buying_triggers
            existing_profile.exclusions = icp_schema_result.exclusion_criteria
            icp_profile = existing_profile
        else:
            icp_profile = ICPProfile(
                product_id=product.id,
                industries=icp_schema_result.industries,
                company_size_min=icp_schema_result.min_employees,
                company_size_max=icp_schema_result.max_employees,
                geographies=icp_schema_result.geographies,
                buyer_roles=icp_schema_result.buyer_roles,
                pain_points=icp_schema_result.pain_points,
                technologies=icp_schema_result.technologies,
                buying_triggers=icp_schema_result.buying_triggers,
                exclusions=icp_schema_result.exclusion_criteria
            )
            db.add(icp_profile)

        db.commit()
        db.refresh(icp_profile)
        return icp_profile
