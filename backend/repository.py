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
        return self._from_snapshot(snapshot)

    def save(self, application: LoanApplication) -> None:
        self.collection.document(application.application_id).set(
            application.model_dump(mode="json")
        )

    def list(self) -> list[LoanApplication]:
        return [
            self._from_snapshot(snapshot)
            for snapshot in self.collection.stream()
        ]

    @staticmethod
    def _from_snapshot(snapshot) -> LoanApplication:
        data = snapshot.to_dict()
        # Applications created before inactivity resets were introduced do
        # not have this field. Their last mutation is the best migration
        # value and allows abandoned legacy records to be reset as expected.
        if not data.get("last_activity_at"):
            data["last_activity_at"] = (
                data.get("updated_at") or data.get("created_at")
            )
        return LoanApplication.model_validate(data)


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
