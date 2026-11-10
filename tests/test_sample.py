def test_sample_route_returns_only_fixed_csv(client):
    response = client.get("/sample.csv")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment" in response.headers["Content-Disposition"]
    assert b"Category,Estimated,Actual" in response.data
    assert b"Emergency repairs" in response.data
    assert client.get("/sample_data/").status_code == 404
    assert client.get("/sample.csv/../../.env").status_code == 404
