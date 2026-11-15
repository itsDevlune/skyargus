import pytest


def test_resolver_returns_canonical_identity_and_reference_limits(monkeypatch):
    from apps.core import providers

    response = b"""<Sesame><Resolver name='SIMBAD'>
      <oname>Barnard's Star</oname><jradeg>269.452075</jradeg><jdedeg>4.693391</jdedeg>
      <refPos>ICRS</refPos><pm><pmRA>-802.33</pmRA><pmDE>10362.53</pmDE></pm>
    </Resolver></Sesame>"""
    requested = []
    monkeypatch.setattr(providers, "get", lambda url, **kwargs: requested.append((url, kwargs)) or response)

    result = providers.resolve("Barnard's Star")

    assert result["name"] == "Barnard's Star"
    assert result["ra"] == pytest.approx(269.452075)
    assert result["dec"] == pytest.approx(4.693391)
    assert result["unit"] == "deg"
    assert "SIMBAD" in result["resolver"]
    assert result["reference"] == "ICRS"
    assert result["pmra_mas_yr"] == "-802.33"
    assert result["pmdec_mas_yr"] == "10362.53"
    assert "Proper motion not applied" in result["epoch"]
    assert "J2000" in result["epoch"]
    assert requested[0][1]["limit"] == 1024 * 1024
    assert "Barnard%27s%20Star" in requested[0][0]


@pytest.mark.parametrize(
    "xml",
    [
        b"<Sesame />",
        b"<Sesame><Target><Resolver><jradeg>1</jradeg><jdedeg>2</jdedeg></Resolver></Target>"
        b"<Target><Resolver><jradeg>3</jradeg><jdedeg>4</jdedeg></Resolver></Target></Sesame>",
        b"<Sesame><Resolver><jradeg>1</jradeg></Resolver></Sesame>",
    ],
)
def test_resolver_rejects_unknown_or_incomplete_results(monkeypatch, xml):
    from apps.core import providers

    monkeypatch.setattr(providers, "get", lambda *args, **kwargs: xml)
    with pytest.raises(ValueError, match="unknown or ambiguous"):
        providers.resolve("not a catalog object")


@pytest.mark.parametrize("ra,dec", [("nan", "0"), ("361", "0"), ("1", "-91")])
def test_resolver_rejects_nonfinite_or_out_of_range_coordinates(monkeypatch, ra, dec):
    from apps.core import providers

    xml = f"<Sesame><Resolver name='SIMBAD'><oname>Object</oname><jradeg>{ra}</jradeg>" \
        f"<jdedeg>{dec}</jdedeg></Resolver></Sesame>".encode()
    monkeypatch.setattr(providers, "get", lambda *args, **kwargs: xml)
    with pytest.raises(ValueError, match="coordinates"):
        providers.resolve("Object")
