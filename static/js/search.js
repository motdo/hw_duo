window.onload = async function () {
    loadContacts();
};


// ======================
// 연락처 불러오기
// ======================
async function loadContacts() {
    const res = await fetch("/search/api");
    const data = await res.json();

    renderTable(data.contacts);
}


// ======================
// 테이블 출력
// ======================
function renderTable(contacts) {
    const table = document.getElementById("tableBody");

    table.innerHTML = "";

    contacts.forEach(contact => {
        table.innerHTML += `
            <tr>
                <td>${contact.name}</td>
                <td>${contact.phone || ""}</td>
                <td>${contact.email || ""}</td>

                <td>
                    <button onclick="editContact(
                        ${contact.id},
                        '${contact.name}',
                        '${contact.phone || ""}',
                        '${contact.email || ""}'
                    )">
                        수정
                    </button>

                    <button onclick="deleteContact(${contact.id})">
                        삭제
                    </button>
                </td>
            </tr>
        `;
    });
}


// ======================
// 추가
// ======================
async function addContact() {
    const name = document.getElementById("name").value;
    const phone = document.getElementById("phone").value;
    const email = document.getElementById("email").value;

    const formData = new FormData();

    formData.append("name", name);
    formData.append("phone", phone);
    formData.append("email", email);

    await fetch("/search/contacts", {
        method: "POST",
        body: formData
    });

    document.getElementById("name").value = "";
    document.getElementById("phone").value = "";
    document.getElementById("email").value = "";

    loadContacts();
}


// ======================
// 수정
// ======================
async function editContact(id, oldName, oldPhone, oldEmail) {

    const name = prompt("이름 수정", oldName);
    if (name === null) return;

    const phone = prompt("전화번호 수정", oldPhone);
    if (phone === null) return;

    const email = prompt("이메일 수정", oldEmail);
    if (email === null) return;

    const formData = new FormData();

    formData.append("name", name);
    formData.append("phone", phone);
    formData.append("email", email);

    await fetch(`/search/contacts/${id}`, {
        method: "POST",
        body: formData
    });

    loadContacts();
}


// ======================
// 삭제
// ======================
async function deleteContact(id) {

    if (!confirm("삭제하시겠습니까?")) {
        return;
    }

    await fetch(`/search/contacts/${id}/delete`, {
        method: "POST"
    });

    loadContacts();
}


// ======================
// 검색
// ======================
async function searchContacts() {

    const q = document.getElementById("searchInput").value;

    const res = await fetch(`/search/api?q=${q}`);
    const data = await res.json();

    renderTable(data.contacts);
}