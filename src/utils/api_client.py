import openai
import time
import logging
import json
import re
from typing import List, Dict

class OpenAIClient:
    """Cliente para interação com API OpenAI - Versão Eficiente"""
    
    def __init__(self, api_key: str, model: str = "gpt-4.1"):
        self.api_key = api_key  
        openai.api_key = api_key
        self.model = model
        self.logger = logging.getLogger(__name__)
    
    def create_revision_prompt(self) -> str:
        """Prompt para identificar APENAS erros"""
        return """Você é um revisor gramatical de material didático.

TAREFA: Identifique APENAS erros gramaticais reais e retorne as correções.

FORMATO DE RESPOSTA OBRIGATÓRIO:
{
  "corrections": [
    {"line": 1, "error": "palavra_errada", "correction": "palavra_correta", "type": "tipo_erro"},
    {"line": 5, "error": "os menino", "correction": "os meninos", "type": "concordância"}
  ]
}

Se NÃO houver erros, retorne: {"corrections": []}

REGRAS CRÍTICAS:
1. Corrija APENAS erros de: ortografia, concordância, acentuação, pontuação obrigatória
2. NUNCA corrija conteúdo de questões ou alternativas
3. PRESERVE erros propositais em alternativas (são pedagógicos)
4. NÃO adicione ponto final em títulos, entenda o contexto ao ler o material
5. IGNORE marcações entre < > ou [ ]
6. line = número da linha aproximado onde está o erro

IMPORTANTE: Retorne APENAS o JSON, sem explicações."""
    
    def identify_errors_batch(self, texts: List[str], callback=None) -> List[Dict]:
        """Identifica erros em lote de textos"""
        all_corrections = []
        
        for i, text in enumerate(texts):
            if callback:
                callback(i + 1, len(texts))
            
            if not text or len(text.strip()) < 3:
                continue
            
            try:
                corrections = self.identify_errors(text, i)
                if corrections:
                    all_corrections.extend(corrections)
            except Exception as e:
                self.logger.error(f"Erro ao analisar texto {i + 1}: {str(e)}")
        
        return all_corrections
    
    # No método identify_errors do api_client.py, corrija:

    def identify_errors(self, text: str, text_index: int = 0) -> List[Dict]:
        """Identifica apenas os erros no texto"""
        prompt = self.create_revision_prompt()
        
        # Adiciona números de linha para referência
        lines = text.split('\n')
        numbered_text = '\n'.join([f"{i+1}: {line}" for i, line in enumerate(lines)])
        
        for attempt in range(3):
            try:
                # SEMPRE usa max_completion_tokens para gpt-4o-mini
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": numbered_text}
                    ],
                    temperature=0.1,
                    max_tokens=10000,  # Usa sempre este
                    top_p=0.1,
                    frequency_penalty=0,
                    presence_penalty=0
                )
                
                result = response.choices[0].message.content.strip()
                
                # Parse JSON
                try:
                    data = json.loads(result)
                    corrections = data.get('corrections', [])
                    
                    # Adiciona índice do texto para cada correção
                    for corr in corrections:
                        corr['text_index'] = text_index
                    
                    return corrections
                    
                except json.JSONDecodeError:
                    self.logger.error(f"Resposta não é JSON válido: {result}")
                    return []
                    
            except Exception as e:
                self.logger.error(f"Tentativa {attempt + 1} falhou: {str(e)}")
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    return []
        
        return []
    

    # No api_client.py, adicione este método:

    def identify_errors_precise(self, text: str, block_index: int = 0) -> List[Dict]:
        """Identifica erros com MÁXIMA precisão - não deixa NADA passar"""
        
        prompt = """Você é um revisor EXTREMAMENTE MINUCIOSO. Sua missão é encontrar TODOS os erros gramaticais.

    ANALISE CADA PALAVRA, CADA VÍRGULA, CADA ACENTO!

    Procure POR:
    1. TODA palavra com ortografia errada
    2. TODO acento faltando ou incorreto  
    3. TODA concordância verbal/nominal errada
    4. TODA vírgula obrigatória faltando
    5. TODO ponto final faltando em parágrafos
    6. TODA crase faltando ou sobrando
    7. TODA letra que deveria ser maiúscula

    Para cada parágrafo marcado como [PARÁGRAFO X], examine PALAVRA POR PALAVRA.

    FORMATO DE RESPOSTA:
    {
    "corrections": [
        {"paragraph": 1, "error": "texto_errado", "correction": "texto_correto", "type": "tipo"},
        {"paragraph": 5, "error": "pra", "correction": "para", "type": "ortografia"}
    ]
    }

    IMPORTANTE:
    - O número do parágrafo é o X em [PARÁGRAFO X]
    - Seja OBSESSIVO com detalhes
    - É melhor reportar demais do que de menos
    - Examine CADA palavra como se fosse a última
    - Verifique concordância de TODOS os substantivos com adjetivos
    - Verifique concordância de TODOS os sujeitos com verbos
    - Verifique TODA pontuação

    [TIPO: TÍTULO/CABEÇALHO] = não adicione ponto final
    [TIPO: ITEM DE LISTA] = preserve formatação de lista
    [TIPO: CÉLULA DE TABELA] = texto de tabela
    [TIPO: PARÁGRAFO NORMAL] = DEVE terminar com ponto final

    Se não houver NENHUM erro: {"corrections": []}"""
        
        # Mesma lógica de chamada mas com prompt mais rigoroso
        return self.identify_errors(text, block_index)