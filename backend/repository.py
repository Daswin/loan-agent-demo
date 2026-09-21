import os
from typing import Dict, Protocol

from .models import LoanApplication


class ApplicationRepository(Protocol):
    def create(self, application: LoanApplication) -> None: ...
    def get(self, application_id: str) -> LoanApplication | None: ...
    def save(self, application: LoanApplication) -> None: ...
    def list(self) -> list[LoanApplication]: ...


class InMemoryApplicationRepository:
    def __init__(self, applications: Dict[str, LoanApplication]):
        self.applications = applications

    def create(self, application: LoanApplication) -> None:
        self.applications[application.application_id] = application

    def get(self, application_id: str) -> LoanApplication | None:
        return self.applications.get(application_id)

    def save(self, application: LoanApplication) -> None:
        self.applications[application.application_id] = application

    def list(self) -> list[LoanApplication]:
        return list(self.applications.values())


class FirestoreApplicationRepository:
    def __init__(self, collection_name: str = "loan_applications"):
        from google.cloud import firestore

        self.collection = firestore.Client().collection(collection_name)

    def create(self, application: LoanApplication) -> None:
        document = self.collection.document(application.application_id)
        if document.get().exists:
            raise ValueError(
                f"Application '{application.application_id}' already exists."
            )
        document.set(application.model_dump(mode="json"))

    def get(self, application_id: str) -> LoanApplication | None:
        snapshot = self.collection.document(application_id).get()
        if not snapshot.exists:
            return None
        return LoanApplication.model_validate(snapshot.to_dict())

    def save(self, application: LoanApplication) -> None:
        self.collection.document(application.application_id).set(
            application.model_dump(mode="json")
        )

    def list(self) -> list[LoanApplication]:
        return [
            LoanApplication.model_validate(snapshot.to_dict())
            for snapshot in self.collection.stream()
        ]


def build_repository(
    memory_store: Dict[str, LoanApplication],
) -> ApplicationRepository:
    store = os.environ.get("APPLICATION_STORE", "memory").strip().lower()
    if store == "memory":
        return InMemoryApplicationRepository(memory_store)
    if store == "firestore":
        collection = os.environ.get(
            "FIRESTORE_COLLECTION",
            "loan_applications",
        )
        return FirestoreApplicationRepository(collection)
    raise ValueError(
        "APPLICATION_STORE must be either 'memory' or 'firestore'."
    )
