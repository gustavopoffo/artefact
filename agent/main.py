"""
Ponto de entrada CLI para testar o agente.

Uso:
    python -m agent.main

Ou importar diretamente:
    from agent import Agent
    agent = Agent()
    response = agent.chat("Vocês têm violão Yamaha?")
"""

import sys
from .chat import Agent


def main():
    """Loop interativo de chat."""
    print("=" * 60)
    print("EMPORIO DA MUSICA — Agente Conversacional")
    print("=" * 60)
    print("Digite sua mensagem ou 'sair' para encerrar.\n")

    agent = Agent(channel="cli")
    session_id = agent.get_session_id()
    print(f"Sessao iniciada: {session_id[:8]}...\n")

    while True:
        try:
            user_input = input("Voce: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nEncerrando...")
            break

        if not user_input:
            continue

        if user_input.lower() in ("sair", "exit", "quit"):
            print("\nAte logo! Obrigado por visitar o Emporio da Musica.")
            break

        try:
            response = agent.chat(user_input)

            print(f"\nAgente: {response.content}")
            print(f"  [modelo={response.model_used}, tokens={response.tokens_input}+{response.tokens_output}, "
                  f"tempo={response.response_time_ms}ms, rag_chunks={response.rag_chunks_used}]\n")

        except Exception as e:
            print(f"\n[ERRO] {e}\n")


if __name__ == "__main__":
    main()
