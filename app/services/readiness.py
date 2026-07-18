from app.core.config import Settings
from app.schemas.readiness import ReadinessCheck


class ReadinessService:
    """Executa as verificações necessárias para a aplicação receber tráfego."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def run_checks(self) -> list[ReadinessCheck]:
        """Executa todas as verificações de prontidão disponíveis."""

        return [
            self._check_configuration(),
        ]

    @staticmethod
    def is_ready(checks: list[ReadinessCheck]) -> bool:
        """Informa se todas as verificações foram concluídas com sucesso."""

        return all(check.status == "ok" for check in checks)

    def _check_configuration(self) -> ReadinessCheck:
        """Verifica se as configurações essenciais estão preenchidas."""

        has_required_settings = bool(
            self._settings.app_name.strip()
            and self._settings.app_version.strip()
            and self._settings.environment.strip()
        )

        if has_required_settings:
            return ReadinessCheck(
                name="configuration",
                status="ok",
            )

        return ReadinessCheck(
            name="configuration",
            status="error",
        )
