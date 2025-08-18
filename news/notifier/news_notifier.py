# news_notifier.py
"""
Notifier: envio de digests de notícias "fresh" por Outlook (desktop) ou Teams (Incoming Webhook).

- Classe Notifier encapsula configuração e provedores (get_all_news).
- Filtro: status == "fresh" e published >= now - window_hours.
- Métodos públicos principais:
    - collect_fresh_news(hours=None)
    - render_email_html(items)
    - notify_outlook(hours=None, to=None, subject_prefix="[NewsTracker]")
    - notify_teams(hours=None, webhook_url=None, title=None, summary_text=None)

Requisitos:
- Outlook: Windows + Outlook Desktop + pywin32
- Teams: URL de Incoming Webhook
- Opcional: python-dotenv para carregar SEND_TO / TEAMS_WEBHOOK_URL do .env

Exemplo:
    from news_notifier import Notifier
    from news.storage.repository import get_all_news

    notifier = Notifier.from_env(get_all_news)
    notifier.notify_outlook(hours=2)  # usa SEND_TO do .env

Autor: você :)
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import os
import html
import json
import platform

# Tipagem leve do provider
GetAllNewsFn = Callable[[], Iterable[Any]]


class Notifier:
    """Encapsula coleta, formatação e envio de digests de notícias."""

    def __init__(
        self,
        get_all_news: GetAllNewsFn,
        default_to: Optional[str] = None,
        teams_webhook_url: Optional[str] = None,
        default_window_hours: int = 2,
    ) -> None:
        """
        Parameters
        ----------
        get_all_news : callable
            Função que retorna iterável de itens de notícia. Cada item deve ter
            campos/atributos: status, published, title, link, sentiment, source, topic, region.
        default_to : str, optional
            E-mail padrão para Outlook (fallback quando `to` não é passado).
        teams_webhook_url : str, optional
            Webhook padrão do Teams (fallback quando `webhook_url` não é passado).
        default_window_hours : int
            Janela padrão (horas) para filtrar itens fresh.
        """
        self._get_all_news = get_all_news
        self.default_to = default_to
        self.teams_webhook_url = teams_webhook_url
        self.default_window_hours = default_window_hours

    # ---------- Fábrica baseada em .env ----------
    @classmethod
    def from_env(
        cls,
        get_all_news: GetAllNewsFn,
        load_env: bool = True,
        dotenv_override: bool = True,
        default_window_hours: int = 2,
    ) -> "Notifier":
        """Cria Notifier lendo SEND_TO e TEAMS_WEBHOOK_URL do .env (se disponível)."""
        if load_env:
            try:
                from dotenv import load_dotenv  # type: ignore
                load_dotenv(override=dotenv_override)
            except Exception:
                # silencioso: seguimos apenas com variáveis do ambiente
                pass
        return cls(
            get_all_news=get_all_news,
            default_to=os.getenv("SEND_TO"),
            teams_webhook_url=os.getenv("TEAMS_WEBHOOK_URL"),
            default_window_hours=default_window_hours,
        )

    # ---------- Helpers internos ----------
    @staticmethod
    def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
        if not ts:
            return None
        try:
            dt = datetime.fromisoformat(ts)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None

    @staticmethod
    def _get(item: Any, name: str, default: Any = None) -> Any:
        """Acessa campo tanto para dict quanto para objeto."""
        if isinstance(item, dict):
            return item.get(name, default)
        return getattr(item, name, default)

    @staticmethod
    def _group_by_topic(items: List[Any]) -> Dict[Tuple[str, str], List[Any]]:
        groups: Dict[Tuple[str, str], List[Any]] = {}
        for it in items:
            topic = Notifier._get(it, "topic") or "Unknown"
            region = (Notifier._get(it, "region") or "GLOBAL").upper()
            key = (topic, region)
            groups.setdefault(key, []).append(it)
        return groups

    @staticmethod
    def _is_windows() -> bool:
        return platform.system() == "Windows"

    # ---------- Coleta e renderização ----------
    def collect_fresh_news(self, hours: Optional[int] = None) -> List[Any]:
        """
        Retorna itens com status 'fresh' e publicados na janela definida.

        Parameters
        ----------
        hours : int, optional
            Janela em horas. Se None, usa self.default_window_hours.
        """
        h = hours if hours is not None else self.default_window_hours
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=h)

        items: List[Any] = []
        for n in self._get_all_news():
            if self._get(n, "status") != "fresh":
                continue
            dt = self._parse_iso(self._get(n, "published"))
            if dt and dt >= cutoff:
                items.append(n)

        # Mais recentes primeiro
        items.sort(key=lambda x: self._get(x, "published") or "", reverse=True)
        return items

    # --- dentro de Notifier (substitua/adicione estes métodos) ---

    def _humanize_dt(self, ts_str: str, now: Optional[datetime] = None) -> str:
        dt = self._parse_iso(ts_str)
        if not dt:
            return ""
        now = now or datetime.now(timezone.utc)
        delta = now - dt
        mins = int(delta.total_seconds() // 60)
        if mins < 1:
            return "agora"
        if mins < 60:
            return f"{mins} min atrás"
        hours = mins // 60
        if hours < 24:
            return f"{hours} h atrás"
        days = hours // 24
        return f"{days} d atrás"

    def _host_from_link(self, link: Optional[str]) -> str:
        if not link:
            return ""
        try:
            host = urlparse(link).netloc or ""
            return host.replace("www.", "")
        except Exception:
            return ""

    def _sentiment_chip(self, sentiment: str) -> str:
        s = (sentiment or "").strip().lower()
        if s.startswith("pos"):
            # verde
            return ("<span style='display:inline-block;background:#D1E7DD;"
                    "color:#0F5132;border-radius:12px;padding:2px 8px;"
                    "font-size:12px;line-height:1;'>Positivo</span>")
        if s.startswith("neg"):
            # vermelho
            return ("<span style='display:inline-block;background:#F8D7DA;"
                    "color:#842029;border-radius:12px;padding:2px 8px;"
                    "font-size:12px;line-height:1;'>Negativo</span>")
        # neutro
        return ("<span style='display:inline-block;background:#E9ECEF;"
                "color:#495057;border-radius:12px;padding:2px 8px;"
                "font-size:12px;line-height:1;'>Neutro</span>")

    def render_email_html(
        self,
        items: List[Any],
        window_hours: Optional[int] = None,
        max_per_topic: int = 20,
    ) -> str:
        """
        HTML compatível com Outlook: tabela (role=presentation), estilos inline e
        chips de sentimento. Mantém compatibilidade com chamadas existentes.
        """
        if not items:
            return "<p style='font-family:Segoe UI,Arial,sans-serif;font-size:14px'>Sem notícias fresh na janela.</p>"

        # janela informativa no topo
        h = window_hours if window_hours is not None else self.default_window_hours

        # Agrupa por (topic, region)
        groups = self._group_by_topic(items)

        # Cabeçalho
        html_parts: List[str] = []
        html_parts.append(
            "<div style='font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#212529'>"
            f"<h2 style='margin:0 0 12px'>News Tracker — Fresh (últimas {h}h)</h2>"
            f"<div style='margin:0 0 12px;color:#6c757d'>Total: {len(items)} item(s)</div>"
        )

        # Para cada grupo, bloco com título + tabela
        for (topic, region), lst in groups.items():
            # limita por tópico, se necessário
            shown = lst[:max_per_topic]
            extra = len(lst) - len(shown)

            html_parts.append(
                f"<h3 style='margin:18px 0 6px;border-top:1px solid #dee2e6;padding-top:10px'>"
                f"{html.escape(region)} — {html.escape(topic)} "
                f"<span style='color:#6c757d;font-weight:normal'>({len(lst)})</span>"
                f"</h3>"
            )

            # tabela "presentation" para Outlook
            html_parts.append(
                "<table role='presentation' cellspacing='0' cellpadding='0' border='0' "
                "style='width:100%;border-collapse:collapse;margin:0 0 8px'>"
            )

            for it in shown:
                title = html.escape(self._get(it, "title") or "")
                link = html.escape(self._get(it, "link") or "#")
                sent = (self._get(it, "sentiment") or "").strip()
                chip = self._sentiment_chip(sent) if sent else ""
                src = self._get(it, "source") or ""
                host = self._host_from_link(self._get(it, "link"))
                ts_iso = self._get(it, "published") or ""
                ts_rel = self._humanize_dt(ts_iso)

                # linha
                html_parts.append(
                    "<tr>"
                    # bullet
                    "<td valign='top' style='width:18px;padding:6px 6px 6px 0'>•</td>"
                    # conteúdo
                    "<td valign='top' style='padding:6px 0'>"
                    f"<div style='margin:0 0 2px'><a href='{link}' "
                    "style='color:#0d6efd;text-decoration:none;'>"
                    f"{title}</a></div>"
                    f"<div style='font-size:12px;color:#6c757d'>"
                    f"{html.escape(src)}{(' — ' + host) if host else ''}"
                    f"{(' — ' + chip) if chip else ''}"
                    f"{(' — ' + html.escape(ts_rel)) if ts_rel else ''}"
                    f"{(' — ' + html.escape(ts_iso)) if ts_iso else ''}"
                    "</div>"
                    "</td>"
                    "</tr>"
                )

            html_parts.append("</table>")

            if extra > 0:
                html_parts.append(
                    f"<div style='font-size:12px;color:#6c757d;margin:-4px 0 8px'>+{extra} item(s) não exibidos…</div>"
                )

        html_parts.append("</div>")
        return "".join(html_parts)

    # ---------- Envios ----------
    def send_via_outlook(self, to: Optional[str], subject: str, html_body: str) -> None:
        """Envia via Outlook (COM). Usa a conta padrão se `to` não for informado."""
        if not self._is_windows():
            raise RuntimeError("Outlook COM é suportado apenas no Windows.")
        try:
            import win32com.client  # type: ignore
        except Exception as e:
            raise RuntimeError("pywin32 é necessário para automação do Outlook. pip install pywin32") from e

        outlook = win32com.client.Dispatch("Outlook.Application")
        session = outlook.Session
        if not to:
            try:
                exch_user = session.CurrentUser.AddressEntry.GetExchangeUser()
                to = exch_user.PrimarySmtpAddress if exch_user else session.CurrentUser.Address
            except Exception:
                to = session.CurrentUser.Address

        mail = outlook.CreateItem(0)  # olMailItem
        mail.To = to
        mail.Subject = subject
        mail.HTMLBody = html_body
        mail.Send()

    def send_to_teams(self, webhook_url: str, title: str, summary_text: str, items: List[Any]) -> None:
        """Posta um card simples em um Incoming Webhook do Teams."""
        import requests  # local import para evitar dependência quando não usado

        # Lista compacta (limites de payload)
        lines: List[str] = []
        for it in items[:50]:
            t = f"[F] {self._get(it, 'title')} ({self._get(it, 'source')})"
            lines.append(f"- {t[:180]}")

        payload = {"title": title, "text": summary_text + "\n\n" + "\n".join(lines)}
        resp = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()

    # ---------- Orquestração de alto nível ----------
    def notify_outlook(
        self,
        hours: Optional[int] = None,
        to: Optional[str] = None,
        subject_prefix: str = "[NewsTracker]",
    ) -> Dict[str, Any]:
        """
        Coleta itens fresh da janela e envia via Outlook.
        Retorna dicionário com status e contagem.
        """
        to = to or self.default_to
        if not to:
            return {"status": "error", "error": "Destinatário não definido (passe `to` ou defina SEND_TO)."}

        items = self.collect_fresh_news(hours)
        if not items:
            return {"status": "no_items", "count": 0, "to": to}

        h = hours if hours is not None else self.default_window_hours
        subject = f"{subject_prefix} {len(items)} fresh item(s) in last {h}h"
        html_body = self.render_email_html(items)
        self.send_via_outlook(to=to, subject=subject, html_body=html_body)
        return {"status": "sent", "count": len(items), "to": to}

    def notify_teams(
        self,
        hours: Optional[int] = None,
        webhook_url: Optional[str] = None,
        title: Optional[str] = None,
        summary_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Coleta itens fresh da janela e envia via Teams (Incoming Webhook).
        Retorna dicionário com status e contagem.
        """
        url = webhook_url or self.teams_webhook_url
        if not url:
            return {"status": "error", "error": "Webhook do Teams não definido (passe `webhook_url` ou defina TEAMS_WEBHOOK_URL)."}

        items = self.collect_fresh_news(hours)
        if not items:
            return {"status": "no_items", "count": 0}

        h = hours if hours is not None else self.default_window_hours
        title = title or f"News Tracker — Fresh (last {h}h)"
        summary_text = summary_text or f"{len(items)} fresh item(s)"
        self.send_to_teams(url, title=title, summary_text=summary_text, items=items)
        return {"status": "sent", "count": len(items)}
