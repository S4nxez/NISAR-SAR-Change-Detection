-- =========================================================
-- V4: English names and descriptions for the demo sites of V3
-- V3 is already applied in every environment, so it is not edited (Flyway
-- would reject its changed checksum): the Spanish texts are updated here.
-- =========================================================

UPDATE sar_site SET name = 'Albufera de Valencia',
    description = 'Wetland near Valencia to simulate changes in flooded area.'
    WHERE id = 'ES_VALENCIA_001';
UPDATE sar_site SET name = 'Donana National Park',
    description = 'Donana wetlands to monitor changes in moisture and flooded area.'
    WHERE id = 'ES_DONANA_001';
UPDATE sar_site SET name = 'Serrania de Cuenca',
    description = 'Forest area to simulate backscatter changes after a wildfire.'
    WHERE id = 'ES_CUENCA_001';
UPDATE sar_site SET name = 'Amazon - Manaus area',
    description = 'Tropical forest area to simulate forest cover loss.'
    WHERE id = 'BR_AMAZON_001';
UPDATE sar_site SET name = 'Pantanal - Mato Grosso do Sul',
    description = 'Pantanal wetlands to simulate seasonal flooding changes.'
    WHERE id = 'BR_PANTANAL_001';
UPDATE sar_site SET name = 'Alberta forests',
    description = 'Canadian forest area to simulate surface changes after a wildfire.'
    WHERE id = 'CA_ALBERTA_001';
UPDATE sar_site SET name = 'Kalimantan - Borneo',
    description = 'Borneo tropical forest to simulate vegetation cover transformation.'
    WHERE id = 'ID_KALIMANTAN_001';
UPDATE sar_site SET name = 'Castilla-La Mancha farmland',
    description = 'Agricultural area to simulate changes in moisture and crop condition.'
    WHERE id = 'ES_CASTILLA_001';
