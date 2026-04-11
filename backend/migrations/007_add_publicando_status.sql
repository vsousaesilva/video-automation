-- Migration 007: Adicionar valor 'publicando' ao enum status_video
-- Sessao 14 — necessario para o orquestrador de publicacao

ALTER TYPE status_video ADD VALUE IF NOT EXISTS 'publicando' AFTER 'aprovado';
