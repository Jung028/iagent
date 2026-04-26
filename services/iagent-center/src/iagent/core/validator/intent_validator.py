from typing import Any, Dict

from iagent.core.intent.contacts import INTENT_REQUIREMENTS
from iagent.core.models.intent import Intent, IntentResult
from iagent.core.models.validation import ValidationResult, ValidationStatus



class IntentValidator: 

    """ 
    we need to sanitise and validate the result is within the intent requirements list,
    in order to decide whether to continue to the orchestrator or to ask for more information 
    from the user
    
    """

    async def validate(
            intent: str, 
            entities: Dict[str, Any]
    ) -> ValidationResult:
        # 1: we check if the intent is within requireements list, else return ValidationResult unidentified /not supported intent

        if intent not in INTENT_REQUIREMENTS: 
            return ValidationResult(
                status=ValidationStatus.INSUFICCIENT_CONTEXT,
                cleaned_entities={},
                missing=[],
            )
        
        # 2: we get the entities, and sanitize it first. 
        cleaned_entities = IntentValidator._sanitize(entities)
        required_fields = INTENT_REQUIREMENTS[intent]["required"]
        # define [] as a list, not a dict {}. 
        missing = []

        # 3: then we find which required fields are not in the cleaned entities, and add to 
        # missing fields to return result to user and ask for them 
        for field in required_fields:
            if field not in cleaned_entities or cleaned_entities[field] in [None, "", []]:
                missing.append(field)
        
        # -- if there is missing, we build the missing model, based on the intent
        if missing: 
            return ValidationResult(
                status=ValidationStatus.INSUFICCIENT_CONTEXT,
                missing=missing,
                question=IntentValidator._build_question(intent, missing),
            )

        # -- else, we will returned the cleaned entities for use in the orchestrator 
        return ValidationResult(
            status=ValidationStatus.READY,
            missing={},
            cleaned_entities=cleaned_entities,
        )

    @staticmethod
    def _sanitize(entities: Dict[str, Any]) -> Dict[str, Any] : 

        # check first if entities is null, then return null 
        if not entities: 
            return {}
        
        #else, we loop through the entities and check whether any is none. 
            
        cleaned = {}
        for key, value in entities.items():
            if value is not None:
                cleaned[key] = value

        return cleaned
            
    @staticmethod
    def _build_question(intent: str, missing: Dict[str, Any]) -> str: 
        if intent == Intent.TRANSACTION_DETAILS.value and "transaction_id" in missing: 
            return "Which transaction are you referring to? Do you have a specific transaction Id or want the latest/oldest/person that you transferred to?"
        
        if intent == Intent.TRANSACTION_SEARCH.value:
            return "What time period should I search? (today, last 7 days, this month)"

        if intent == Intent.TRANSACTION_ANALYZE.value:
            return "What would you like to analyze (spending, income, top transactions) and for which time period?"

        if intent == Intent.BALANCE_INQUIRY.value: 
            return "what would you like to know about your balance"
        
        if intent == Intent.TRANSFER.value: 
            return ""

        return "I need more details to proceed."
    

