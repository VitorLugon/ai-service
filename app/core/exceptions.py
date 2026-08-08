class AIProviderError(RuntimeError):
    """Erro base relacionado ao provedor de inteligência artificial."""

    code = "ai_provider_error"
    public_message = "AI provider request failed."
    retryable = False


class AIProviderConfigurationError(AIProviderError):
    """Indica que o provedor não foi configurado corretamente."""

    code = "ai_provider_not_configured"
    public_message = "AI provider is not configured."


class AIProviderTimeoutError(AIProviderError):
    """Indica que o provedor excedeu o tempo limite."""

    code = "ai_provider_timeout"
    public_message = "AI provider timed out."
    retryable = True


class AIProviderConnectionError(AIProviderError):
    """Indica que não foi possível conectar ao provedor."""

    code = "ai_provider_unreachable"
    public_message = "AI provider is temporarily unreachable."
    retryable = True


class AIProviderRateLimitError(AIProviderError):
    """Indica que o limite temporário do provedor foi atingido."""

    code = "ai_provider_rate_limited"
    public_message = "AI provider rate limit was reached."
    retryable = True


class AIProviderUnavailableError(AIProviderError):
    """Indica indisponibilidade interna do provedor."""

    code = "ai_provider_unavailable"
    public_message = "AI provider is temporarily unavailable."
    retryable = True


class AIProviderRequestError(AIProviderError):
    """Indica que o provedor rejeitou a requisição enviada."""

    code = "ai_provider_request_rejected"
    public_message = "AI provider rejected the classification request."


class AIProviderIncompleteResponseError(AIProviderError):
    """Indica que a geração foi encerrada antes de ser concluída."""

    code = "ai_provider_incomplete_response"
    public_message = "AI provider returned an incomplete response."


class AIProviderRefusalError(AIProviderError):
    """Indica que o modelo recusou a classificação."""

    code = "ai_provider_refused"
    public_message = "AI provider refused to classify the ticket."


class AIProviderInvalidResponseError(AIProviderError):
    """Indica que o provedor não retornou o contrato esperado."""

    code = "ai_provider_invalid_response"
    public_message = "AI provider returned an invalid response."


class KnowledgeStoreError(RuntimeError):
    """Erro base relacionado ao armazenamento vetorial de conhecimento."""

    code = "knowledge_store_error"
    public_message = "Knowledge store request failed."
    retryable = False


class KnowledgeBaseNotIndexedError(KnowledgeStoreError):
    """Indica que a base persistente ainda não foi indexada."""

    code = "knowledge_base_not_indexed"
    public_message = "Knowledge base has not been indexed."


class KnowledgeStoreConfigurationError(KnowledgeStoreError):
    """Indica configuração incompatível do armazenamento de conhecimento."""

    code = "knowledge_store_configuration_error"
    public_message = "Knowledge store configuration is invalid."


class KnowledgeStoreUnavailableError(KnowledgeStoreError):
    """Indica indisponibilidade temporária do armazenamento de conhecimento."""

    code = "knowledge_store_unavailable"
    public_message = "Knowledge store is temporarily unavailable."
    retryable = True
