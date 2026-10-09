from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "model",
    "civic_nlp_model"
)


tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_PATH
)

model.eval()


def predict_complaint(text):

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128
    )


    with torch.no_grad():

        outputs = model(**inputs)

        prediction = torch.argmax(
            outputs.logits,
            dim=1
        ).item()


    category = model.config.id2label[prediction]

    return category



if __name__ == "__main__":

    print("Civic NLP Model Ready ✅")
    print("Type 'exit' to stop\n")

    while True:

        complaint = input("Enter complaint: ")

        if complaint.lower() == "exit":
            print("Closing model...")
            break

        result = predict_complaint(complaint)

        print("\nPredicted Category:")
        print(result)
        print("-" * 50)



        """testing sentences 
        garbage  :

        mere ghar ke paas kai din se kachra pada hua hai, safai nahi hui hai

        majhya gharajaval khup divasapasun kachra padla aahe, safai keli nahi
        
        society ke bahar garbage jama hai aur smell aa rahi hai

        
        pothole :
        

        road condition bahut bad hai, bike chalana difficult ho raha hai
 
        There is a huge pothole on the main road causing accidents


        streetlight :
            hamare gali ka street light pichle ek hafte se band hai
            raat ko bahut andhera hota hai kyunki pole ki light kharab hai
            The street light near my house is not working at night


        Water Leakage:
              
        
            pipeline se pani leak ho raha hai aur pura rasta geela ho gaya hai
            pipeline futli aahe ani satat pani vahata aahe
            water pipe damage hai aur pani waste ho raha hai
            There is continuous water leakage from the broken pipeline



        drainage problem:

            nali block ho gayi hai aur ganda pani road par aa raha hai
            nali bharli aahe ani pausache pani gharasamor jama hot aahe
            drainage jam hai, dirty water overflow ho raha hai
            The drainage system is blocked and dirty water is overflowing


        traffic issue :
            is chowk par roz bahut traffic jam hota hai
            Heavy traffic congestion occurs here every morning

        """










