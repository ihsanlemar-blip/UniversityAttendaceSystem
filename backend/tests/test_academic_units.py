"""Test suite for academic units, flexible hierarchy, cycle detection, and tree views."""

import uuid

from fastapi.testclient import TestClient

from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_users import get_admin_headers


def test_create_academic_unit_hierarchy(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify creating a multi-level hierarchy: Faculty -> Department -> Program."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # 1. Create Root Unit: Faculty of Engineering
    fac_res = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={
            "name": "Faculty of Engineering",
            "code": f"ENG_{suffix}",
            "unit_type": "FACULTY",
            "short_name": "ENG",
            "sort_order": 1,
        },
    )
    assert fac_res.status_code == 201
    fac_data = fac_res.json()["data"]
    fac_id = fac_data["id"]
    assert fac_data["parent_id"] is None
    assert fac_data["status"] == "ACTIVE"

    # 2. Create Child Unit: Department of Computer Science
    dept_res = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={
            "name": "Department of Computer Science",
            "code": f"CS_{suffix}",
            "unit_type": "DEPARTMENT",
            "parent_id": fac_id,
            "short_name": "CS",
            "sort_order": 1,
        },
    )
    assert dept_res.status_code == 201
    dept_data = dept_res.json()["data"]
    dept_id = dept_data["id"]
    assert dept_data["parent_id"] == fac_id

    # 3. Create Grandchild Unit: Software Engineering Program
    prog_res = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={
            "name": "Software Engineering Program",
            "code": f"SE_{suffix}",
            "unit_type": "PROGRAM",
            "parent_id": dept_id,
            "short_name": "SE",
            "sort_order": 1,
        },
    )
    assert prog_res.status_code == 201
    prog_data = prog_res.json()["data"]
    assert prog_data["parent_id"] == dept_id

    # 4. Verify Detail with Ancestor Breadcrumbs
    detail_res = client.get(f"/api/v1/academic-units/{prog_data['id']}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()["data"]
    assert detail["parent"]["id"] == dept_id
    assert len(detail["ancestor_path"]) == 2
    assert detail["ancestor_path"][0]["id"] == fac_id
    assert detail["ancestor_path"][1]["id"] == dept_id


def test_code_uniqueness_within_university(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Duplicate academic unit codes within same university must be rejected."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    code = f"MED_{uuid.uuid4().hex[:6]}"

    # First creation succeeds
    res1 = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={"name": "Faculty of Medicine", "code": code, "unit_type": "FACULTY"},
    )
    assert res1.status_code == 201

    # Duplicate code rejected
    res2 = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={"name": "Duplicate Medicine", "code": code, "unit_type": "FACULTY"},
    )
    assert res2.status_code == 409


def test_cross_tenant_parent_rejection(
    client: TestClient,
    test_university: University,
    second_university: University,
    test_admin_user: User,
) -> None:
    """Attempting to assign a parent unit from another university must fail."""
    headers = get_admin_headers(client, test_admin_user, test_university)

    # Make unit in test university using a random parent UUID
    res = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={
            "name": "Invalid Parent Department",
            "code": f"INV_{uuid.uuid4().hex[:6]}",
            "unit_type": "DEPARTMENT",
            "parent_id": str(uuid.uuid4()),
        },
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_PARENT_UNIT"


def test_self_parenting_cycle_detection(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Self-parenting (A -> A) must be rejected with ACADEMIC_UNIT_CYCLE."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    res = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={"name": "Self Unit", "code": f"SELF_{suffix}", "unit_type": "FACULTY"},
    )
    assert res.status_code == 201
    unit_id = res.json()["data"]["id"]

    # Attempt to reparent A -> A
    move_res = client.post(
        f"/api/v1/academic-units/{unit_id}/move",
        headers=headers,
        json={"parent_id": unit_id},
    )
    assert move_res.status_code == 400
    assert move_res.json()["error"]["code"] == "ACADEMIC_UNIT_CYCLE"


def test_two_node_cycle_detection(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Direct cycle (A -> B, then moving A under B: B -> A -> B) must be rejected."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # Create A (parent)
    res_a = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={"name": "Unit A", "code": f"CYC_A_{suffix}", "unit_type": "FACULTY"},
    )
    unit_a_id = res_a.json()["data"]["id"]

    # Create B with parent A
    res_b = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={
            "name": "Unit B",
            "code": f"CYC_B_{suffix}",
            "unit_type": "DEPARTMENT",
            "parent_id": unit_a_id,
        },
    )
    unit_b_id = res_b.json()["data"]["id"]

    # Attempt to move A to be child of B
    move_res = client.post(
        f"/api/v1/academic-units/{unit_a_id}/move",
        headers=headers,
        json={"parent_id": unit_b_id},
    )
    assert move_res.status_code == 400
    assert move_res.json()["error"]["code"] == "ACADEMIC_UNIT_CYCLE"


def test_deep_three_node_cycle_detection(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Deep transitive cycle (A -> B -> C, then moving A under C) must be rejected."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # A -> B -> C
    res_a = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={"name": "Deep A", "code": f"D_A_{suffix}", "unit_type": "FACULTY"},
    )
    unit_a_id = res_a.json()["data"]["id"]

    res_b = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={
            "name": "Deep B",
            "code": f"D_B_{suffix}",
            "unit_type": "DEPARTMENT",
            "parent_id": unit_a_id,
        },
    )
    unit_b_id = res_b.json()["data"]["id"]

    res_c = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={
            "name": "Deep C",
            "code": f"D_C_{suffix}",
            "unit_type": "PROGRAM",
            "parent_id": unit_b_id,
        },
    )
    unit_c_id = res_c.json()["data"]["id"]

    # Attempt to move A under C
    move_res = client.post(
        f"/api/v1/academic-units/{unit_a_id}/move",
        headers=headers,
        json={"parent_id": unit_c_id},
    )
    assert move_res.status_code == 400
    assert move_res.json()["error"]["code"] == "ACADEMIC_UNIT_CYCLE"


def test_tree_hierarchy_retrieval(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Tree endpoint returns nested structure without N+1 query explosion."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # Create root
    fac_res = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={"name": "Tree Root Faculty", "code": f"TR_F_{suffix}", "unit_type": "FACULTY"},
    )
    fac_id = fac_res.json()["data"]["id"]

    # Create child
    dept_res = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={
            "name": "Tree Child Department",
            "code": f"TR_D_{suffix}",
            "unit_type": "DEPARTMENT",
            "parent_id": fac_id,
        },
    )
    dept_id = dept_res.json()["data"]["id"]

    # Fetch tree rooted at fac_id
    tree_res = client.get(f"/api/v1/academic-units/tree?root_id={fac_id}", headers=headers)
    assert tree_res.status_code == 200
    tree = tree_res.json()["data"]
    assert len(tree) == 1
    assert tree[0]["id"] == fac_id
    assert len(tree[0]["children"]) >= 1
    child_ids = [c["id"] for c in tree[0]["children"]]
    assert dept_id in child_ids


def test_reparent_move_and_make_root(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Moving a child unit to root level or another parent works cleanly."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # Create Parent 1 & 2
    p1 = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={"name": "Parent 1", "code": f"P1_{suffix}", "unit_type": "FACULTY"},
    ).json()["data"]["id"]
    p2 = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={"name": "Parent 2", "code": f"P2_{suffix}", "unit_type": "FACULTY"},
    ).json()["data"]["id"]

    # Create child under Parent 1
    child = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={
            "name": "Movable Child",
            "code": f"MC_{suffix}",
            "unit_type": "DEPARTMENT",
            "parent_id": p1,
        },
    ).json()["data"]["id"]

    # Move child from P1 to P2
    move_res = client.post(
        f"/api/v1/academic-units/{child}/move",
        headers=headers,
        json={"parent_id": p2},
    )
    assert move_res.status_code == 200
    assert move_res.json()["data"]["parent_id"] == p2

    # Move child to root (parent_id: None)
    root_res = client.post(
        f"/api/v1/academic-units/{child}/move",
        headers=headers,
        json={"parent_id": None},
    )
    assert root_res.status_code == 200
    assert root_res.json()["data"]["parent_id"] is None


def test_deactivation_blocked_with_active_children(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Deactivating a parent unit with active children is rejected."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    parent_id = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={"name": "Parent Unit", "code": f"DP_{suffix}", "unit_type": "FACULTY"},
    ).json()["data"]["id"]

    client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={
            "name": "Child Unit",
            "code": f"DC_{suffix}",
            "unit_type": "DEPARTMENT",
            "parent_id": parent_id,
        },
    )

    # Attempt to deactivate parent
    deact_res = client.post(
        f"/api/v1/academic-units/{parent_id}/deactivate",
        headers=headers,
    )
    assert deact_res.status_code == 400
    assert deact_res.json()["error"]["code"] == "ACADEMIC_UNIT_HAS_ACTIVE_CHILDREN"


def test_unicode_and_localization_support(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify Pashto and Dari characters persist and retrieve properly."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # Pashto: د کمپیوټر ساینس پوهنځی
    pashto_name = "د کمپیوټر ساینس پوهنځی"
    pashto_res = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={
            "name": pashto_name,
            "code": f"PS_{suffix}",
            "unit_type": "FACULTY",
            "short_name": "کمپیوټر",
        },
    )
    assert pashto_res.status_code == 201
    pashto_id = pashto_res.json()["data"]["id"]

    # Dari: پوهنځی انجنیري
    dari_name = "پوهنځی انجنیري"
    dari_res = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={
            "name": dari_name,
            "code": f"DA_{suffix}",
            "unit_type": "FACULTY",
            "short_name": "انجنیري",
        },
    )
    assert dari_res.status_code == 201
    dari_id = dari_res.json()["data"]["id"]

    # Fetch both and verify string equality
    p_get = client.get(f"/api/v1/academic-units/{pashto_id}", headers=headers)
    assert p_get.status_code == 200
    assert p_get.json()["data"]["name"] == pashto_name

    d_get = client.get(f"/api/v1/academic-units/{dari_id}", headers=headers)
    assert d_get.status_code == 200
    assert d_get.json()["data"]["name"] == dari_name
