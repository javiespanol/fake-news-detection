import re
from telegram.ext import *
from telegram import *
import openai
from urllib.request import urlopen
from bs4 import BeautifulSoup
from transformers import BertTokenizerFast, BertForSequenceClassification
import json


print("Imports done.")

openai.api_key = "API KEY OPENAI"
bot_token = "API TOKEN TELEGRAM"
prompt = "Escribe un resumen de esta noticia con tan solo 40 palabras, en español e incluyendo la fecha de la noticia, repito tan solo 40 palabras"
info_text = "Este bot está diseñado para ayudarte a identificar noticias falsas y desinformación en línea. Sin embargo, es importante tener en cuenta que el resultado proporcionado por el bot es simplemente el resultado de un clasificador basado en un modelo. Aunque se trabaja arduamente para brindar resultados precisos, es posible que en algunas ocasiones se produzcan errores o falsos positivos. Además, se asegura que los datos introducidos en nuestro bot no serán utilizados con ningún otro fin más allá de la detección de fake news."
pattern_url = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
VALIDATE, REGISTER, R_TRUE, R_FAKE, GET_NEWS, G_TRUE, G_FALSE, TRAIN, CANCEL = range(9)

updater=Updater(bot_token, use_context=True)
dp=updater.dispatcher

config_file = "./config/config.json"
train_state = 0
try:
    with open(config_file, encoding="UTF-8") as json_file:
        data = json.load(json_file)
        whitelist = data["userids_users"]
        whitelist_admin = data["userids_admins"]
        train_state = data["train"]
except:
    whitelist = []
    train_state = 0
    
print(train_state)
    
#model.to('cuda')


print("Model created.")
model = "./model/fake-news-javi-1"
max_length = 512


tokenizer = BertTokenizerFast.from_pretrained(model, do_lower_case=True, num_labels=2)
model = BertForSequenceClassification.from_pretrained(model, num_labels=2)

def get_prediction(text, convert_to_label=True):

    inputs = tokenizer(text, padding=True, truncation=True, max_length=max_length, return_tensors="pt")#.to("cuda")
    outputs = model(**inputs)
    probs = outputs[0].softmax(1)
    
    labels = {
        0: "Verdadera",
        1: "Falsa"
    }
    
    if convert_to_label:
      return labels[int(probs.argmax())]
    else:
      return int(probs.argmax())


chat_response = ""
messages = []

messages.append({"role": "assistant", "content": chat_response})



def start(update, context):
    
    userid = update.effective_user.id
    if userid not in whitelist:
        if userid not in data["userids_wait"]:
            data["userids_wait"] = data["userids_wait"] + [userid]
        write_json(data)
        context.bot.send_message(update.message.chat_id, text="Podrás utilizar el bot cuando un administrador dé el alta a tu usuario.")
        print(userid)
        return
    
    if userid in whitelist_admin:
        keyboard = [[InlineKeyboardButton("Validar Noticia 🗞", callback_data=str(VALIDATE))],[InlineKeyboardButton("Registrar Noticia ✏️", callback_data=str(REGISTER))], 
                     [InlineKeyboardButton("Mis Noticias 🗒", callback_data=str(GET_NEWS))],[InlineKeyboardButton("Confirmar Noticias 📌", callback_data=str(TRAIN))],[InlineKeyboardButton("Entrenar Modelo 💪🏻", callback_data=str(TRAIN))]]
    else:
        keyboard = [[InlineKeyboardButton("Validar Noticia 🗞", callback_data=str(VALIDATE))],[InlineKeyboardButton("Registrar Noticia ✏️", callback_data=str(REGISTER))], 
                     [InlineKeyboardButton("Mis Noticias 🗒", callback_data=str(GET_NEWS))]]
        
    context.bot.send_message(update.message.chat_id, text="Escoja una opción:", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data['choice'] = -1
    
def info(update, context):
    context.bot.send_message(update.message.chat_id, text=info_text)  
    start(update, context)
    
def deletetrue(update, context):
    
    userid = update.effective_user.id
    if userid not in whitelist:
        if userid not in data["userids_wait"]:
            data["userids_wait"] = data["userids_wait"] + [userid]
        write_json(data)
        context.bot.send_message(update.message.chat_id, text="Podrás utilizar el bot cuando un administrador dé el alta a tu usuario.")
        print(userid)
        return
    
    context.bot.send_message(update.message.chat_id, text="Eliminando tus noticias verdaderas registradas.") 
    delete_news(userid, "true")
    
    start(update, context)
    
def deletefake(update, context):
    userid = update.effective_user.id
    if userid not in whitelist:
        if userid not in data["userids_wait"]:
            data["userids_wait"] = data["userids_wait"] + [userid]
        write_json(data)
        context.bot.send_message(update.message.chat_id, text="Podrás utilizar el bot cuando un administrador dé el alta a tu usuario.")
        print(userid)
        return
    
    context.bot.send_message(update.message.chat_id, text="Eliminando tus noticias falsas registradas.") 
    delete_news(userid, "fake")
    
    start(update, context)

def echo(update, context):
    
    userid = update.effective_user.id
    if userid not in whitelist:
        if userid not in data["userids_wait"]:
            data["userids_wait"] = data["userids_wait"] + [userid]
        write_json(data)
        context.bot.send_message(update.message.chat_id, text="Podrás utilizar el bot cuando un administrador dé el alta a tu usuario.")
        print(userid)
        return
    
    print(context.user_data['choice'])

    if context.user_data['choice'] == -1:
        pass
        
    elif context.user_data['choice'] == 0:
        result = get_prediction(update.message.text)       
        context.bot.send_message(chat_id=update.effective_chat.id, text="Noticia validada, resultado: <b>" + result + "</b>", parse_mode=ParseMode.HTML)
        context.user_data['choice'] = -1
        
    elif context.user_data['choice'] == 2:
        matches = re.findall(pattern_url,update.message.text)
        if len(matches)>=1:
            try:
                url=matches[0][0]
                context.bot.send_message(chat_id=update.effective_chat.id, text="Resumiendo noticia, esta operación puede tardar unos segundos.")
                texto = resumir(url)
            except:
                texto = "ERROR"
        else:
            texto = update.message.text
        
        if not texto.__eq__("ERROR"):
            write_file("true", texto, userid)
            context.bot.send_message(chat_id=update.effective_chat.id, text="Noticia registrada como <b>VERDADERA</b> ✅.", parse_mode=ParseMode.HTML)
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Noticia invalidada.", parse_mode=ParseMode.HTML)
        
            
        context.user_data['choice'] = -1
        
    elif context.user_data['choice'] == 3:
        matches = re.findall(pattern_url,update.message.text)
        if len(matches)>=1:
            try:
                url=matches[0][0]
                texto = resumir(url)
            except:
                texto = "ERROR"
        else:
            texto = update.message.text
        
        if not texto.__eq__("ERROR"):
            write_file("fake", texto, userid)
            context.bot.send_message(chat_id=update.effective_chat.id, text="Noticia registrada como <b>FALSA</b> ❎.", parse_mode=ParseMode.HTML)
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Noticia invalidada.", parse_mode=ParseMode.HTML)
        
        context.user_data['choice'] = -1
        
        

    start(update, context)
   
def buttons(update, context):
    
    userid = update.effective_user.id
    if userid not in whitelist:
        if userid not in data["userids_wait"]:
            data["userids_wait"] = data["userids_wait"] + [userid]
        write_json(data)
        context.bot.send_message(update.message.chat_id, text="Podrás utilizar el bot cuando un administrador dé el alta a tu usuario.")
        print(userid)
        return
    
    query = update.callback_query
    query.answer()

    if query.data == str(VALIDATE):
        context.bot.send_message(chat_id=query.message.chat_id, text="Ingrese la noticia a validar:")

        # Registramos el estado de la conversación
        context.user_data['choice'] = VALIDATE
        return VALIDATE

    elif query.data == str(REGISTER):

        keyboard = [[InlineKeyboardButton("Verdadera", callback_data=str(R_TRUE)),InlineKeyboardButton("Falsa", callback_data=str(R_FAKE))]]
        context.bot.send_message(chat_id=query.message.chat_id, text="Seleccione si es <b>VERDADERA</b> ✅ o <b>FALSA</b> ❎", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

        # Registramos el estado de la conversación
        context.user_data['choice'] = REGISTER
        return REGISTER
    
    elif query.data == str(R_TRUE):
        context.bot.send_message(chat_id=query.message.chat_id, text="Escriba solamente el <b>link</b> o la noticia <b>VERADERA</b> ✅:", parse_mode=ParseMode.HTML)
    
        # Registramos el estado de la conversación
        context.user_data['choice'] = R_TRUE
        return R_TRUE
    
    elif query.data == str(R_FAKE):
        context.bot.send_message(chat_id=query.message.chat_id, text="Escriba solamente el <b>link</b> o la noticia <b>FALSA</b> ❎:", parse_mode=ParseMode.HTML)
    
        # Registramos el estado de la conversación
        context.user_data['choice'] = R_FAKE
        return R_FAKE
    
    elif query.data == str(GET_NEWS):
        keyboard = [[InlineKeyboardButton("Verdaderas", callback_data=str(G_TRUE)),InlineKeyboardButton("Falsas", callback_data=str(G_FALSE))]]
    
        context.bot.send_message(chat_id=query.message.chat_id, text="Seleccione que noticias desea ver:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
        # Registramos el estado de la conversación
        context.user_data['choice'] = GET_NEWS
        return GET_NEWS
    
    elif query.data == str(G_TRUE):
        # Registramos el estado de la conversación
        text = get_news(userid, "true")
        context.bot.send_message(chat_id=query.message.chat_id, text=text, parse_mode=ParseMode.HTML)
        #context.user_data['choice'] = G_TRUE
        aux_start(userid,context,query)
    
    elif query.data == str(G_FALSE):
        # Registramos el estado de la conversación
        text = get_news(userid, "fake")
        context.bot.send_message(chat_id=query.message.chat_id, text=text, parse_mode=ParseMode.HTML)
        #context.user_data['choice'] = G_FALSE
        aux_start(userid,context,query)
    
    elif query.data == str(TRAIN):
        train_state = data["train"]
        if train_state==1:
            context.bot.send_message(chat_id=query.message.chat_id, text="El modelo ya se está entrenando.", parse_mode=ParseMode.HTML)

        else:
            train_state = 1
            data["train"] = 1
            write_json(data)
            context.bot.send_message(chat_id=query.message.chat_id, text="Iniciando entrenamiento.", parse_mode=ParseMode.HTML)
        
        aux_start(userid,context,query)
         
         
            
def aux_start(userid,context,query):
    if userid in whitelist_admin:
        keyboard = [[InlineKeyboardButton("Validar Noticia 🗞", callback_data=str(VALIDATE))],[InlineKeyboardButton("Registrar Noticia ✏️", callback_data=str(REGISTER))], 
                    [InlineKeyboardButton("Mis Noticias 🗒", callback_data=str(GET_NEWS))],[InlineKeyboardButton("Confirmar Noticias 📌", callback_data=str(TRAIN))],[InlineKeyboardButton("Entrenar Modelo 💪🏻", callback_data=str(TRAIN))]]
    else:
        keyboard = [[InlineKeyboardButton("Validar Noticia 🗞", callback_data=str(VALIDATE))],[InlineKeyboardButton("Registrar Noticia ✏️", callback_data=str(REGISTER))], 
                    [InlineKeyboardButton("Mis Noticias 🗒", callback_data=str(GET_NEWS))]]
        
    context.bot.send_message(query.message.chat_id, text="Escoja una opción:", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data['choice'] = -1
   
   
def delete_news(userid, type):
    text_file = open("user_news/"+str(userid) +"_"+type+'_news_bot.txt', "w", encoding="UTF-8")
    text_file.close()

def write_json(data):
    with open(config_file, 'w', encoding="UTF-8") as fp:
        json_dumps_str = json.dumps(data, indent=4)
        fp.write(json_dumps_str)
        
def get_news(userid, type):
    try:
        text_file = open("user_news/"+str(userid) +"_"+type+'_news_bot.txt', "r", encoding="UTF-8")
        text = text_file.read()
        text_file.close()
    except:
        text="No hay noticias."
    
    if text.__eq__(""):
        text="No hay noticias."
    
    text = text.replace("\n", "\n\n")
    return text
    
def write_file(filetype, text, userid):
    file = open("user_news/"+str(userid) +"_"+filetype+'_news_bot.txt', 'a', encoding="UTF-8")
    file.write(text+"\n")
    file.close()
    
def resumir(url):
    
    html = urlopen(url).read()
    soup = BeautifulSoup(html, features="html.parser")

    for script in soup(["script", "style"]):
        script.extract()

    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    noticia = '\n'.join(chunk for chunk in chunks if chunk)
    
    messages = []
    messages.append({"role": "user", "content": noticia})

    try:
        
        messages.append({"role": "user", "content": prompt})
        
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )

        chat_response = completion.choices[0].message.content

        messages.append({"role": "assistant", "content": chat_response})
            
    except:
        print("ERROR")
    
    return chat_response
 

def cancel(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="La operación ha sido cancelada.")
    print("CANCEL")
    del context.user_data['choice']

    return ConversationHandler.END

deletetrue_handler = CommandHandler('deletetrue', deletetrue)
dp.add_handler(deletetrue_handler)

deletefake_handler = CommandHandler('deletefake', deletefake)
dp.add_handler(deletefake_handler)

start_handler = CommandHandler('start', start)
dp.add_handler(start_handler)

info_handler = CommandHandler('info', info)
dp.add_handler(info_handler)

echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
dp.add_handler(echo_handler)

button_handler = CallbackQueryHandler(buttons)
dp.add_handler(button_handler)
    
    
print("Server started.")

updater.start_polling()
updater.idle()