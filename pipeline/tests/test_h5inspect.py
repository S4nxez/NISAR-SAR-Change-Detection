import h5py
import numpy as np

from irrigation_footprint.h5inspect import dump


def test_dump_lists_groups_datasets_attributes_and_small_values(tmp_path):
    path = tmp_path / "product.h5"
    with h5py.File(path, "w") as f:
        f.attrs["mission"] = "NISAR"
        ident = f.create_group("science/LSAR/identification")
        ident.create_dataset("orbitPassDirection", data=b"Descending")
        grid = f.create_group("science/LSAR/GUNW/grids/frequencyA/unwrappedInterferogram/HH")
        phase = grid.create_dataset("unwrappedPhase", data=np.zeros((50, 40), dtype="float32"))
        phase.attrs["units"] = b"radians"
        grid.create_dataset("projection", data=np.uint32(32611)).attrs["epsg_code"] = 32611

    text = dump(path)
    assert "@mission = NISAR" in text
    assert "science/LSAR/identification/orbitPassDirection  () object = Descending" in text
    assert "unwrappedPhase  (50, 40) float32" in text
    assert "@units = radians" in text
    assert "projection  () uint32 = 32611" in text and "@epsg_code = 32611" in text
    # large arrays are summarised, not printed
    assert "0.0, 0.0" not in text
