#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
┌────────────────────────────────────────────────────────────┐
│                                                                            │
│       ⛨  VALHEIM TRANSLATOR  ⛨                                          │
│          By the power of Odin                                          │
│                                                                            │
│  ⚡ Tradução paralela ultrarrrápida                                         │
│  🛡️  Cache inteligente (só traduz o que falta)                          │
│  ⚔️  Preserva blocos YAML multilinha                                     │
│  🎯 Retry automático em falhas                                           │
│  🇵🇹 Inglês → Português BR                                                │
│                                                                            │
└────────────────────────────────────────────────────────────┘
"""

import os
import re
import time
import json
from typing import Dict, List, Tuple, Optional
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor, as_completed

# Estrutura de pastas organizada
PASTA_ORIGINAL = "Original"
PASTA_TRADUZIDO = "Traduzido"
PASTA_CACHE = "Cache"

ARQ_ENTRADA = os.path.join(PASTA_ORIGINAL, "collected_items.yaml")
ARQ_SAIDA = os.path.join(PASTA_TRADUZIDO, "translations.yaml")
ARQ_CACHE = os.path.join(PASTA_CACHE, "translations_cache.json")

# ------------------------- Utilidades YAML -------------------------

def _strip_quotes(s: str) -> Tuple[str, Optional[str]]:
    s = s.strip()
    if (len(s) >= 2) and ((s[0] == s[-1]) and s[0] in "'\""):
        return s[1:-1], s[0]
    return s, None

def _quote_yaml(s: str) -> str:
    # Usa sempre aspas duplas e escapa internas
    return '"' + s.replace('"', '\\"') + '"'

def _is_block_start(line: str) -> bool:
    ls = line.strip()
    # Inícios comuns de blocos multilinha no arquivo coletado
    return (
        ls.startswith('? >-') or
        ls.startswith(': >-') or
        ls.endswith(': >-') or  # key: >-
        ls == '|-' or ls == '>' or ls == '|'
    )

# ------------------- Heurísticas para pular traduções -------------------

def _should_skip_key(norm_key: str) -> bool:
    # Evita traduzir ids/nomes técnicos
    if len(norm_key) < 3:
        return True
    if norm_key.startswith('$'):
        return True
    if norm_key.startswith(('piece_', 'rae_', 'Ymir', 'RuneSphere_', 'IG_', 'sapling_', 'Pickable_', 'PineTree_', 'Ashwood_', 'Yagluth')):
        return True
    if norm_key.endswith('_TW'):
        return True
    # Muitos underlines normalmente indicam id técnico
    if norm_key.count('_') >= 2 and re.fullmatch(r"[\w\-\[\]]+", norm_key):
        return True
    return False

# ---------------------- Tradução e cache ----------------------

def _load_cache() -> Dict[str, str]:
    cache = {}
    if os.path.exists(ARQ_CACHE):
        try:
            with open(ARQ_CACHE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except Exception:
            cache = {}
    return cache

def _save_cache(cache: Dict[str, str]) -> None:
    try:
        with open(ARQ_CACHE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _merge_existing_translations(cache: Dict[str, str]) -> Dict[str, str]:
    # Lê translations.yaml atual (se existir) e incorpora no cache
    if not os.path.exists(ARQ_SAIDA):
        return cache
    try:
        with open(ARQ_SAIDA, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception:
        return cache

    in_block = False
    block_indent_level = None
    for line in lines:
        raw = line.rstrip('\n')
        if in_block:
            # Termina bloco quando a indentação cai
            if raw.strip() == '' or (raw and not raw.startswith(' ') and not raw.startswith('\t')):
                in_block = False
            continue
        if _is_block_start(raw):
            in_block = True
            continue
        if ':' not in raw:
            continue
        key_part, val_part = raw.split(':', 1)
        k_norm, _ = _strip_quotes(key_part.strip())
        v_norm, _ = _strip_quotes(val_part.strip())
        if k_norm and v_norm and k_norm != v_norm:
            cache.setdefault(k_norm, v_norm)
    return cache


def _translate_with_retry(text: str, translator: GoogleTranslator, retries: int = 3) -> str:
    """Traduz texto com retry exponencial otimizado"""
    delay = 0.3  # Delay inicial reduzido de 0.4 para 0.3
    for attempt in range(retries):
        try:
            return translator.translate(text)
        except Exception:
            if attempt == retries - 1:
                return text
            time.sleep(delay)
            delay *= 1.8  # Multiplicador reduzido de 2 para 1.8


def _translate_batch(texts: List[str]) -> Dict[str, str]:
    # Cada thread usa seu próprio tradutor para reduzir contenção
    translator = GoogleTranslator(source='en', target='pt')
    out = {}
    for t in texts:
        out[t] = _translate_with_retry(t, translator)
    return out

# ---------------------- Pipeline principal ----------------------

def main() -> None:
    t0 = time.time()  # Iniciar cronômetro
    print("\n" + "="*60)
    print("⚨  VALHEIM TRANSLATOR  ⚨")
    print("By the power of Odin - Tradução em velocidade de raio!")
    print("="*60)

    # Cria pastas se não existirem
    for pasta in [PASTA_ORIGINAL, PASTA_TRADUZIDO, PASTA_CACHE]:
        os.makedirs(pasta, exist_ok=True)

    if not os.path.exists(ARQ_ENTRADA):
        print(f"❌ ERRO: Arquivo '{ARQ_ENTRADA}' não encontrado!")
        print(f"   Coloque o arquivo 'collected_items.yaml' na pasta '{PASTA_ORIGINAL}/")
        return

    # Carrega arquivo coletado
    with open(ARQ_ENTRADA, 'r', encoding='utf-8-sig') as f:
        linhas = f.readlines()
    print(f"Total de linhas: {len(linhas)}")

    # Carrega cache e incorpora translations.yaml existente
    cache = _load_cache()
    cache = _merge_existing_translations(cache)

    # 1) Identificar candidatos a traduzir
    print("\n🔍 Fase 1: Identificando textos para traduzir…")
    textos_para_traduzir: List[str] = []
    mapa_linhas: Dict[int, Tuple[str, str]] = {}  # linha -> (key_raw, key_norm)

    in_block = False
    for i, line in enumerate(linhas):
        raw = line.rstrip('\n')
        if in_block:
            # Fim do bloco quando linha não-indentada ou vazia após pelo menos 1 linha
            if raw.strip() == '' or (raw and not raw.startswith(' ') and not raw.startswith('\t')):
                in_block = False
            continue
        if _is_block_start(raw):
            in_block = True
            continue
        if not raw or raw.lstrip().startswith('#'):
            continue
        if ':' not in raw:
            continue
        key_part, val_part = raw.split(':', 1)
        key_raw = key_part.strip()
        val_raw = val_part.strip()
        k_norm, k_q = _strip_quotes(key_raw)
        v_norm, v_q = _strip_quotes(val_raw)
        # Só traduz quando key == value (após normalização)
        if k_norm == v_norm and not _should_skip_key(k_norm):
            textos_para_traduzir.append(k_norm)
            mapa_linhas[i] = (key_raw, k_norm)

    if not textos_para_traduzir:
        print("   ✓ Nada para traduzir. Gerando arquivo final apenas com o que já existe…")
        # Apenas reescreve o arquivo de saída preservando
        with open(ARQ_SAIDA, 'w', encoding='utf-8') as f:
            f.writelines(linhas)
        return

    # 2) Remover duplicatas mantendo ordem
    textos_unicos = list(dict.fromkeys(textos_para_traduzir))
    print(f"   ✓ Encontrados {len(textos_unicos)} textos únicos para traduzir")

    # 3) Determinar o que falta traduzir (usa cache)
    faltando = [t for t in textos_unicos if t not in cache]
    print(f"   ✓ Já em cache: {len(textos_unicos) - len(faltando)} | A traduzir agora: {len(faltando)}")

    # 4) Traduz em paralelo (em lotes)
    if faltando:
        print("\n⚡ Fase 2: Traduzindo em paralelo…")
        tamanho_lote = 80  # Otimizado: lotes maiores para melhor throughput
        lotes = [faltando[i:i + tamanho_lote] for i in range(0, len(faltando), tamanho_lote)]
        max_threads = min(10, len(lotes))  # Aumentado de 8 para 10 threads

        traduzidas_tmp: Dict[str, str] = {}
        inicio_traducao = time.time()
        with ThreadPoolExecutor(max_workers=max_threads) as ex:
            futures = [ex.submit(_translate_batch, lote) for lote in lotes]
            concluidas = 0
            total = len(lotes)
            for fut in as_completed(futures):
                res = fut.result()
                traduzidas_tmp.update(res)
                concluidas += 1
                percent = (concluidas * 100) // total
                elapsed = time.time() - inicio_traducao
                items_traduzidos = sum(len(lote) for lote in lotes[:concluidas])
                taxa = items_traduzidos / elapsed if elapsed > 0 else 0
                print(f"   Progresso: {concluidas}/{total} lotes ({percent}%) | {items_traduzidos}/{len(faltando)} itens | {taxa:.1f} itens/s")

        # Atualiza cache
        cache.update(traduzidas_tmp)
        _save_cache(cache)
    else:
        print("   ✓ Nada novo para traduzir — utilizando traduções do cache/arquivo existente")

    # 5) Gerar arquivo final substituindo apenas valores elegíveis
    print("\n📝 Fase 3: Gerando arquivo traduzido…")
    saida: List[str] = []
    in_block = False
    for i, line in enumerate(linhas):
        raw = line.rstrip('\n')
        if in_block:
            saida.append(raw + '\n')
            if raw.strip() == '' or (raw and not raw.startswith(' ') and not raw.startswith('\t')):
                in_block = False
            continue
        if _is_block_start(raw):
            saida.append(raw + '\n')
            in_block = True
            continue
        if i in mapa_linhas:
            key_raw, k_norm = mapa_linhas[i]
            traduzida = cache.get(k_norm, k_norm)
            saida.append(f"{key_raw}: {_quote_yaml(traduzida)}\n")
        else:
            saida.append(raw + '\n')

    # 6) Salvar resultado
    with open(ARQ_SAIDA, 'w', encoding='utf-8') as f:
        f.writelines(saida)

    # Sumário final detalhado
    tempo_total = time.time() - t0
    print("\n" + "=" * 60)
    print("✅ TRADUÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 60)
    print(f"📊 Estatísticas:")
    print(f"   • Total de textos únicos: {len(textos_unicos)}")
    print(f"   • Do cache: {len(textos_unicos) - len(faltando)}")
    print(f"   • Traduzidos agora: {len(faltando)}")
    if len(faltando) > 0 and tempo_total > 0:
        taxa_media = len(faltando) / tempo_total
        print(f"   • Taxa média: {taxa_media:.1f} traduções/segundo")
    print(f"\n💾 Arquivo salvo: {ARQ_SAIDA}")
    print(f"⏱️  Tempo total: {tempo_total:.1f} segundos")
    print("=" * 60)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tradução interrompida pelo usuário.")
    except Exception as e:
        print(f"\n\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
