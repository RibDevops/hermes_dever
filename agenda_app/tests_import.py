#!/usr/bin/env python3
"""Testes automatizados com mocks para o comando import_agenda.

Somente unittest + unittest.mock. Nenhuma chamada real de rede/Telegram.
Tokens e credenciais aqui sao ficticios.
"""
from unittest.mock import patch, MagicMock

from django.test import TestCase

from agenda_app.models import AgendaItem, PortalCredential, Turma
from agenda_app.management.commands.import_agenda import (
    autenticar,
    listar_eventos,
    Command,
)


class ImportAgendaTests(TestCase):
    """Testes unitarios do management command import_agenda sem chamadas reais."""

    def setUp(self):
        self.turma = Turma.objects.create(
            nome="Turma Teste", grade="12",
            class_id="109576", profile="13", school="1846", ativa=True,
        )
        PortalCredential.objects.create(
            turma=self.turma, usuario_portal="teste_user",
            senha_portal="teste_senha",
        )

    def _make_session(self, auth_token="test-token"):
        """Sessao ficticia com header Authorization (padrao da implementacao)."""
        s = MagicMock()
        s.headers = {"Authorization": "Bearer " + auth_token}
        return s

    def _make_cred(self):
        return PortalCredential.objects.get(turma=self.turma)

    # ---------- 1. login bem-sucedido e extracao do token ----------
    @patch("agenda_app.management.commands.import_agenda.requests.Session")
    def test_login_bem_sucedido_e_extracao_do_token(self, mock_session_cls):
        session = MagicMock()
        session.headers = {}
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"token": "fake-token-123"}
        session.post.return_value = resp
        mock_session_cls.return_value = session

        sessao = autenticar(self._make_cred())

        self.assertIs(sessao, session)
        self.assertEqual(session.headers["Authorization"], "Bearer fake-token-123")
        _, kwargs = session.post.call_args
        self.assertEqual(
            kwargs["json"], {"email": "teste_user", "password": "teste_senha"}
        )

    # ---------- 2. resposta de login sem token ----------
    @patch("agenda_app.management.commands.import_agenda.requests.Session")
    def test_resposta_login_sem_token(self, mock_session_cls):
        session = MagicMock()
        session.headers = {}
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"outro": "dado"}
        session.post.return_value = resp
        mock_session_cls.return_value = session

        with self.assertRaisesRegex(ValueError, "Token n.o encontrado"):
            autenticar(self._make_cred())

    # ---------- 3. paginacao com duas paginas ----------
    def test_paginacao_duas_paginas(self):
        session = self._make_session()
        page1 = MagicMock()
        page1.raise_for_status.return_value = None
        page1.json.return_value = {"data": list(range(100))}
        page2 = MagicMock()
        page2.raise_for_status.return_value = None
        page2.json.return_value = {"data": list(range(100, 130))}
        session.get.side_effect = [page1, page2]

        eventos = listar_eventos(session)

        self.assertEqual(len(eventos), 130)
        self.assertEqual(session.get.call_count, 2)

    # ---------- 4. resposta em formato lista (top-level) ----------
    def test_resposta_formato_lista(self):
        session = self._make_session()
        session.get.return_value.raise_for_status.return_value = None
        session.get.return_value.json.return_value = [
            {"id": 1, "title": "Evento lista"}
        ]

        eventos = listar_eventos(session)

        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["id"], 1)

    # ---------- 5. formatos results, data, items e events ----------
    def test_resposta_formatos_results_data_items_events(self):
        for chave, eid in (("results", 1), ("data", 2),
                           ("items", 3), ("events", 4)):
            with self.subTest(chave=chave):
                session = self._make_session()
                session.get.return_value.raise_for_status.return_value = None
                session.get.return_value.json.return_value = {
                    chave: [{"id": eid}]
                }

                eventos = listar_eventos(session)

                self.assertEqual(len(eventos), 1)
                self.assertEqual(eventos[0]["id"], eid)

    # ---------- 6. evento sem id, externalId ou uuid e ignorado ----------
    def test_evento_sem_id_externalid_uuid_e_ignorado(self):
        cmd = Command()
        criados, _ = cmd.importar(self.turma, [
            {"title": "Sem ID"},
            {"id": "x-99", "title": "Com ID"},
        ])

        self.assertEqual(criados, 1)
        self.assertEqual(AgendaItem.objects.filter(external_id="").count(), 0)
        self.assertTrue(
            AgendaItem.objects.filter(external_id="x-99").exists()
        )

    # ---------- 7. evento sem anexos ----------
    def test_evento_sem_anexos(self):
        cmd = Command()
        criados, com_pdf = cmd.importar(self.turma, [
            {"id": "s1", "title": "Sem anexos", "startDate": "2026-01-01"},
        ])

        self.assertEqual(criados, 1)
        self.assertEqual(com_pdf, 0)
        item = AgendaItem.objects.get(external_id="s1")
        self.assertEqual(item.download_url, "")

    # ---------- 8. anexo PDF valido ----------
    def test_anexo_pdf_valido(self):
        cmd = Command()
        criados, com_pdf = cmd.importar(self.turma, [
            {
                "id": "p1",
                "title": "Com PDF",
                "attachments": [
                    {"url": "https://example.com/doc.pdf"},
                ],
            },
        ])

        self.assertEqual(criados, 1)
        self.assertEqual(com_pdf, 1)
        item = AgendaItem.objects.get(external_id="p1")
        self.assertTrue(item.download_url.endswith(".pdf"))

    # ---------- 9. erro HTTP na autenticacao ----------
    @patch("agenda_app.management.commands.import_agenda.requests.Session")
    def test_erro_http_autenticacao(self, mock_session_cls):
        session = MagicMock()
        session.headers = {}
        resp = MagicMock()
        resp.raise_for_status.side_effect = Exception("401 Client Error")
        session.post.return_value = resp
        mock_session_cls.return_value = session

        with self.assertRaisesRegex(Exception, "401"):
            autenticar(self._make_cred())

    # ---------- 10. erro HTTP na consulta de eventos ----------
    def test_erro_http_consulta_eventos(self):
        session = self._make_session()
        session.get.side_effect = Exception("500 Server Error")

        with self.assertRaisesRegex(Exception, "500"):
            listar_eventos(session)

    # ---------- 11. importacao idempotente com update_or_create ----------
    def test_importacao_idempotente(self):
        cmd = Command()
        eventos = [{"id": "ev-001", "title": "A"}]

        criados1, _ = cmd.importar(self.turma, eventos=eventos)
        criados2, _ = cmd.importar(self.turma, eventos=eventos)

        self.assertEqual(criados1, 1)
        self.assertEqual(criados2, 0)
        self.assertEqual(
            AgendaItem.objects.filter(external_id="ev-001").count(), 1
        )

    # ---------- 12. API retornando zero eventos ----------
    def test_api_zero_eventos(self):
        session = self._make_session()
        session.get.return_value.raise_for_status.return_value = None
        session.get.return_value.json.return_value = {"data": []}

        eventos = listar_eventos(session)

        self.assertEqual(eventos, [])

    # ---------- contrato: helper entrega Authorization ----------
    def test_make_session_tem_authorization(self):
        session = self._make_session()

        self.assertIn("Authorization", session.headers)
        self.assertTrue(
            session.headers["Authorization"].startswith("Bearer ")
        )

    # ---------- contrato: listar_eventos rejeita sessao sem Authorization ----------
    def test_listar_eventos_rejeita_sessao_sem_authorization(self):
        session = MagicMock()
        session.headers = {}

        with self.assertRaisesRegex(
            ValueError,
            "Sess.o sem Authorization; token nao definido",
        ):
            listar_eventos(session)

    # ---------- 13. author importado de contact.name ----------
    def test_author_importado(self):
        cmd = Command()
        cmd.importar(self.turma, [
            {"id": "a1", "title": "T",
             "contact": {"name": "Profa Ficticia"}},
        ])
        item = AgendaItem.objects.get(external_id="a1")
        self.assertEqual(item.author, "Profa Ficticia")

    # ---------- 14. time importado de startTime/endTime ----------
    def test_time_importado(self):
        cmd = Command()
        cmd.importar(self.turma, [
            {"id": "t1", "title": "T",
             "startTime": "07:10:00", "endTime": "23:59:00"},
        ])
        item = AgendaItem.objects.get(external_id="t1")
        self.assertEqual(item.time, "07:10 – 23:59")

    # ---------- 15. type importado ----------
    def test_type_importado(self):
        cmd = Command()
        cmd.importar(self.turma, [
            {"id": "ty1", "title": "T", "type": "assignment"},
        ])
        item = AgendaItem.objects.get(external_id="ty1")
        self.assertEqual(item.type, "assignment")

    # ---------- 16. multiplos links preservados ----------
    def test_multiplos_links_preservados(self):
        cmd = Command()
        cmd.importar(self.turma, [
            {"id": "m1", "title": "T",
             "links": ["https://example.com/a.pdf",
                       "https://example.com/b.png"]},
        ])
        item = AgendaItem.objects.get(external_id="m1")
        self.assertEqual(item.links, ["https://example.com/a.pdf",
                                      "https://example.com/b.png"])

    # ---------- 17. pdf, png e docx preservados; download so PDF ----------
    def test_links_pdf_png_docx_e_download_apenas_pdf(self):
        cmd = Command()
        _, com_pdf = cmd.importar(self.turma, [
            {"id": "f1", "title": "T",
             "attachments": [
                 {"url": "https://example.com/img.png"},
                 {"url": "https://example.com/doc.docx"},
                 {"url": "https://example.com/primeiro.pdf"},
                 {"url": "https://example.com/segundo.pdf"},
             ]},
        ])
        item = AgendaItem.objects.get(external_id="f1")
        self.assertEqual(len(item.links), 4)
        self.assertIn("https://example.com/img.png", item.links)
        self.assertIn("https://example.com/doc.docx", item.links)
        self.assertEqual(item.download_url,
                         "https://example.com/primeiro.pdf")
        self.assertEqual(com_pdf, 1)

    # ---------- 18. evento sem links continua funcionando ----------
    def test_evento_sem_links_novos_campos_default(self):
        cmd = Command()
        cmd.importar(self.turma, [
            {"id": "n1", "title": "Sem links"},
        ])
        item = AgendaItem.objects.get(external_id="n1")
        self.assertEqual(item.links, [])
        self.assertEqual(item.download_url, "")
        self.assertEqual(item.author, "")
        self.assertEqual(item.time, "")
        self.assertEqual(item.type, "event")

    # ---------- 19. reimportacao com novos campos continua idempotente ----------
    def test_reimportacao_novos_campos_idempotente(self):
        cmd = Command()
        evento = {"id": "r1", "title": "T", "type": "task",
                  "contact": {"name": "Autor X"},
                  "startTime": "07:00:00", "endTime": "08:00:00",
                  "attachments": [{"url": "https://example.com/x.pdf"}]}
        criados1, _ = cmd.importar(self.turma, [evento])
        criados2, _ = cmd.importar(self.turma, [evento])
        self.assertEqual(criados1, 1)
        self.assertEqual(criados2, 0)
        self.assertEqual(
            AgendaItem.objects.filter(external_id="r1").count(), 1)

    # ---------- 20. atualizacao altera novos campos sem duplicata ----------
    def test_atualizacao_novos_campos_sem_duplicata(self):
        cmd = Command()
        cmd.importar(self.turma, [
            {"id": "u1", "title": "T", "type": "task",
             "contact": {"name": "Antigo"},
             "attachments": [{"url": "https://example.com/a.pdf"}]},
        ])
        cmd.importar(self.turma, [
            {"id": "u1", "title": "T novo", "type": "event",
             "contact": {"name": "Novo"},
             "startTime": "12:00:00",
             "links": ["https://example.com/b.png"]},
        ])
        self.assertEqual(
            AgendaItem.objects.filter(external_id="u1").count(), 1)
        item = AgendaItem.objects.get(external_id="u1")
        self.assertEqual(item.title, "T novo")
        self.assertEqual(item.type, "event")
        self.assertEqual(item.author, "Novo")
        self.assertEqual(item.links, ["https://example.com/b.png"])
        self.assertEqual(item.download_url, "")
