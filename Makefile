# Cameroon Poverty Mapping — commandes courantes
# Usage : make help

PYTHON ?= python
PIP    ?= pip

.PHONY: help install test pipeline pipeline-v3 maps maps-full clean

help:
	@echo "Cameroon Poverty Mapping"
	@echo ""
	@echo "  make install       Installer les dépendances (requirements.txt)"
	@echo "  make test          Lancer la suite de tests (pytest)"
	@echo "  make pipeline      Pipeline complet v4 (DHS + GEE + INS + modèle + cartes)"
	@echo "  make pipeline-v3   Pipeline legacy v3 (sans INS)"
	@echo "  make maps          Régénérer cartes v4 (artefacts existants)"
	@echo "  make maps-full     Cartes v4 + inférence raster nationale"
	@echo ""
	@echo "Options :"
	@echo "  make pipeline SKIP_DHS=1 SKIP_GEE=1   Sauter étapes déjà faites"

install:
	$(PIP) install -r requirements.txt

test:
	$(PYTHON) -m pytest tests/ -q

pipeline:
	$(PYTHON) scripts/run_pipeline.py \
		$(if $(SKIP_DHS),--skip-dhs,) \
		$(if $(SKIP_GEE),--skip-gee,) \
		$(if $(SKIP_INS),--skip-ins,) \
		$(if $(SKIP_INFERENCE),--skip-inference,)

pipeline-v3:
	$(PYTHON) scripts/run_pipeline.py --v3 \
		$(if $(SKIP_DHS),--skip-dhs,) \
		$(if $(SKIP_GEE),--skip-gee,)

maps:
	$(PYTHON) scripts/make_maps.py --skip-notebook

maps-full:
	$(PYTHON) scripts/make_maps.py --with-inference