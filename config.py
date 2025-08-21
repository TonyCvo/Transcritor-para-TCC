# ========================================
#    CONFIGURAÇÃO DA API KEY
# ========================================
# 
# 1. Copie este arquivo para config.py
# 2. Substitua "sua-api-key-aqui" pela sua API key real
# 3. No arquivo TCC 2.py, substitua a linha da API key por:
#    from config import CLAUDE_API_KEY
#    self.client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

CLAUDE_API_KEY = "sua-api-key-aqui"

# ========================================
#    COMO OBTER UMA API KEY
# ========================================
# 
# 1. Acesse: https://console.anthropic.com/
# 2. Faça login ou crie uma conta
# 3. Vá em "API Keys"
# 4. Clique em "Create Key"
# 5. Copie a chave gerada
# 6. Cole aqui no lugar de "sua-api-key-aqui"
#
# ⚠️  IMPORTANTE: Nunca compartilhe sua API key!
# ⚠️  IMPORTANTE: Não commite este arquivo no git!
# ⚠️  IMPORTANTE: Adicione config.py ao .gitignore
