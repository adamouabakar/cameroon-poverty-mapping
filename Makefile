# Cameroon Poverty Mapping — commandes courantes
# Usage : make help

PYTHON ?= python
PIP    ?= pip

.PHONY: help install test pipeline maps clean

help:
	@echo "Cameroon Poverty Mapping"
	@echo ""
	@echo "  make install    Installer les dépendances (requirements.txt)"
	@echo "  make test       Lancer la suite de tests (pytest)"
	@echo "  make pipeline   Pipeline complet (DHS + GEE + modèle + cartes)"
	@echo "  make maps       Régénérer les cartes uniquement"
	@echo ""
	@echo "Options pipeline :"
	@echo "  make pipeline SKIP_GEE=1   Ignorer extraction GEE"
	@echo "  make pipeline SKIP_DHS=1   Ignorer préparation DHS"

install:
	$(PIP) install -r requirements.txt

test:
	$(PYTHON) -m pytest tests/ -q

pipeline:
	$(PYTHON) scripts/run_pipeline.py \
		$(if $(SKIP_DHS),--skip-dhs,) \
		$(if $(SKIP_GEE),--skip-gee,)

maps:
	$(PYTHON) scripts/regenerate_maps.py