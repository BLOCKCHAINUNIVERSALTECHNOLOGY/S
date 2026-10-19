// sai.chat — AI chat (real when S_AI_KEY + S_AI_URL set)
fn ask(prompt: str): str {
    ret __sai_ask(prompt)
}

fn chat(message: str): str {
    ret __sai_ask(message)
}

fn system_prompt(role: str): str {
    print "[SAI] system role:", role
    ret role
}
