window.onload = function () {
    loadAll();
};

function loadAll() {
    fetch("/api/contacts")
        .then(res => res.json())
        .then(data => renderTable(data));
}

function search() {
    const keyword = document.getElementById("searchInput").value;

    fetch("/api/contacts?keyword=" + keyword)
        .then(res => res.json())
        .then(data => renderTable(data));
}

function addContact() {
    const name = document.getElementById("name").value;
    const phone = document.getElementById("phone").value;

    fetch("/api/contacts", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ name, phone })
    })
    .then(res => res.json())
    .then(() => loadAll());
}

function renderTable(data) {
    let html = "";

    data.forEach(item => {
        html += `
            <tr>
                <td>${item.name}</td>
                <td>${item.phone}</td>
            </tr>
        `;
    });

    document.getElementById("tableBody").innerHTML = html;
}