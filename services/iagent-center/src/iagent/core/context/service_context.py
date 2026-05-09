from dataclasses import dataclass

@dataclass
class ServiceContext: 
    user_id: str
    phone_no: str
    request_id: str=""
    session_id: str=""
    auth_token: str | None = None

    def to_kwargs(self) -> dict[str, str]: 
        kwargs : dict[str, str] = {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "workflow_id": self.session_id,
        }
        if self.auth_token: 
            kwargs["auth_token"] = self.auth_token
        return kwargs 

