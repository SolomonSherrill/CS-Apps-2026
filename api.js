const api = "https://robotics-backend-ddu8.onrender.com"

async function login(username, password) {
    const response = await fetch(`${api}/login`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username, password})
    })
    return response.json()
}

async function getInventory() {
    const response = await fetch(`${api}/inventory/all`)
    return response.json()
}