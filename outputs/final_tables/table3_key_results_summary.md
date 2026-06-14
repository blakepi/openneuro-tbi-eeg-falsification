| domain | metric | value | interpretation | source |
| --- | --- | --- | --- | --- |
| D1 acute broad artifact-controlled family | minimum q | 0.7876 | Does not survive broad artifact-controlled FDR. | outputs/qc/final_result_consistency_checks.csv |
| D1 narrow prior-anchor family | transparency-family q | 0.1320 | Exploratory only and not a claim rescue. | outputs/qc/d1_d3_model_family_audit.csv |
| D3 posterior eyes-closed alpha/IAF | minimum q | 0.9149 | Does not rescue the acute signal. | outputs/qc/final_result_consistency_checks.csv |
| Chronic TBI branch | minimum q | 0.3484 | Separate, exploratory, and batch-sensitive. | outputs/qc/final_result_consistency_checks.csv |
| D2 DPX cue-baseline | minimum q and max abs(g) | q=0.0898; abs(g)=0.5277 | Weak/context-specific trace. | reports/35_d2_bounded_falsification_report.md |
| D2 task-average and mixed models | minimum q and count | DPX q=0.1524; VWM q=0.4720; mixed count=0 | Does not support robust cross-task convergence. | outputs/d2_cross_task/d2_falsification_summary.csv |
| ds003490 comparator | retrieval and readiness | 75 paired SET/FDT; MNE readable | Comparator and pipeline rehearsal only. | reports/20_ds003490_full_retrieval_report.md |
