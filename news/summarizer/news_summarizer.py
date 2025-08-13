import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM

class NewsSummarizer:
    """
    Classe para sumarização de notícias multilíngue (português/inglês) usando mT5-small XLSum.
    Usa prefixo 'PT ' ou 'EN ' no texto para indicar o idioma.
    Gera resumo abstrativo, pode ser guiado via prompt para listar tópicos.
    """

    def __init__(self, model_name="fernandals/mt5-small-finetuned-xlsum-en-pt"):
        self.device = 0 if torch.cuda.is_available() else -1
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        self.pipe = pipeline(
            "summarization",
            model=self.model,
            tokenizer=self.tokenizer,
            device=self.device
        )

    def summarize(
        self, 
        text: str,
        language: str = "pt",
        max_lines: int = 10,
        prompt: str = None
    ) -> str:
        """
        Gera resumo do texto fornecido.
        :param text: Texto original da notícia.
        :param language: 'pt' ou 'en'
        :param max_lines: Limite de linhas do resumo (aproximado).
        :param prompt: Instrução opcional (para bullet points).
        :return: Resumo como string.
        """
        lang_prefix = "PT" if language.lower().startswith("pt") else "EN"
        # Adicione prompt instrucional para formato em tópicos/bullets
        if not prompt:
            if language.lower().startswith("pt"):
                prompt = f"Liste os principais pontos da notícia abaixo em até {max_lines} tópicos:\n"
            else:
                prompt = f"List the key takeaways from the following news in up to {max_lines} bullet points:\n"
        # Combine prefixo de idioma, prompt e texto
        input_text = f"{lang_prefix} {prompt}{text.strip()}"
        # Tokens: ~130 tokens costuma dar até 10 frases curtas
        out = self.pipe(
            input_text,
            max_length=130,
            min_length=30,
            do_sample=False,
            truncation=True,
        )
        return out[0]['summary_text'].strip()
