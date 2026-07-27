"""
sujeitos.edp.analise — análises pós-coleta específicas por experimento
(004, 006, 006b, 007), movidas de bancada/scorer.py na FASE B6.

bancada/scorer.py conhece só o genérico (001/003) e os primitivos
compartilhados (wilson, normalize, score_fidelity, valor_concluido,
score_prontuario). Cada módulo aqui é sujeito importando sujeito (permitido)
+ os primitivos de bancada.scorer/bancada.prontuario — nunca o contrário.
"""
