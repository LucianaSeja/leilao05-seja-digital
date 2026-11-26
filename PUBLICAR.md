# Publicar a tela do leilão online (Streamlit Cloud)

Pronto no computador, ainda NÃO publicado. Cada passo abaixo exige o ok da Luciana.

1. Criar um repositório PRIVADO novo no GitHub (ex.: `leilao05-seja-digital`) e enviar o conteúdo desta pasta `online`
   (app.py, requirements.txt, .streamlit/config.toml, .gitignore). NÃO enviar segredos.
2. No Streamlit Cloud: New app > escolher o repositório > arquivo principal `app.py`.
3. Settings > Secrets: colar o modelo de `secrets_exemplo.toml` com os valores reais
   (bloco [dropbox] igual ao do app pdb2027, trocando xlsx_path por estado_path; e [acesso] diretores).
4. Settings > Sharing: deixar o app PRIVADO e convidar só os e-mails que podem ver (diretor, telão, equipe).
5. Ensaio: abrir em 2 aparelhos, clicar INICIAR, ver os dois mudarem, depois Administração > Reiniciar.
6. Antes do leilão: reiniciar (voltar para "aguardando o início").
