"""Área administrativa do Attena (/admin).

Regra de ouro: o admin gerencia METADADOS e a operação da plataforma — nunca o
conteúdo privado dos usuários. Nada neste pacote decifra mensagem, destinatário
ou dado de faturamento (há teste que garante: tests/test_admin_privacy.py).
Não existe rota para ler conversas, mensagens, histórico ou mídia.
"""
