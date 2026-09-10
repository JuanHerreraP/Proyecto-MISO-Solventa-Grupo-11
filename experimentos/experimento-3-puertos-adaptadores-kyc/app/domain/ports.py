"""
Puerto interno IdentityVerificationProvider.

La hipótesis de diseño que este experimento valida es que, mientras el
consumidor dependa únicamente de este puerto, sustituir el proveedor KYC
(Proveedor A -> Proveedor B) debe requerir cero cambios en el servicio de
Identidad y en los demás componentes consumidores.
"""
from abc import ABC, abstractmethod

from app.domain.models import VerificationRequest, VerificationResult


class IdentityVerificationProvider(ABC):
    @abstractmethod
    def verify(self, request: VerificationRequest) -> VerificationResult:
        """Verifica la identidad del solicitante y retorna un resultado en el
        modelo de dominio de Solventa, sin importar qué proveedor externo lo
        resolvió."""
        raise NotImplementedError
