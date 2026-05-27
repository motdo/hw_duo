function search() {
    const q = document.getElementById("searchInput").value;

    fetch(`/search/api?q=${q}`)
        .then(res => res.json())
        .then(data => {
            renderTable(data.contacts);
        });
}

function renderTable(contacts) {
    const tbody = document.getElementById("tableBody");
    tbody.innerHTML = "";

    contacts.forEach(c => {
        tbody.innerHTML += `
            <tr>
                <td>${c.name}</td>
                <td>${c.phone || ""}</td>
                <td>
                    <button onclick="editContact(${c.id}, '${c.name}', '${c.phone}')">수정</button>
                    <button onclick="deleteContact(${c.id})">삭제</button>
                </td>
            </tr>
        `;
    });
}

function addContact() {
    const name = document.getElementById("name").value;
    const phone = document.getElementById("phone").value;

    if (!name) {
        alert("이름을 입력하세요");
        return;
    }

    fetch("/search/contacts", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            name: name,
            phone: phone
        })
    })
    .then(res => {
        if (!res.ok) {
            throw new Error("추가 실패");
        }
        return res.json();
    })
    .then(() => {
        document.getElementById("name").value = "";
        document.getElementById("phone").value = "";
        search();
    })
    .catch(err => {
        console.error(err);
        alert("추가 실패");
    });
}

function editContact(id, name, phone) {
    const newName = prompt("이름", name);
    const newPhone = prompt("전화번호", phone);

    if (!newName) return;

    fetch(`/search/contacts/${id}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            name: newName,
            phone: newPhone
        })
    })
    .then(res => {
        if (!res.ok) {
            throw new Error("수정 실패");
        }
        return res.json();
    })
    .then(() => search())
    .catch(err => {
        console.error(err);
        alert("수정 실패");
    });
}

function deleteContact(id) {
    if (!confirm("삭제하시겠습니까?")) return;

    fetch(`/search/contacts/${id}/delete`, {
        method: "POST"
    })
    .then(res => {
        if (!res.ok) {
            throw new Error("삭제 실패");
        }
        return res.json();
    })
    .then(() => search())
    .catch(err => {
        console.error(err);
        alert("삭제 실패");
    });
}