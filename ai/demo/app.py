import streamlit as st
from PIL import Image

from image_predict import predict_image
from nlp_predict import predict_text
from fusion import combine


st.set_page_config(
    page_title="Civic Intelligence AI",
    layout="centered"
)


st.title("🏙️ Civic Intelligence Platform")

st.write(
    "AI based complaint classification using NLP and Image Classification"
)


# Upload image

uploaded_image = st.file_uploader(
    "Upload Complaint Image",
    type=["jpg", "jpeg", "png"]
)


# Text description

description = st.text_area(
    "Describe the issue",
    placeholder="Example: There is a large pothole on the road near my house"
)


image_result = None
text_result = None


if st.button("🔍 Classify"):


    # Image processing
    if uploaded_image:

        image = Image.open(uploaded_image)

        st.image(
            image,
            caption="Uploaded Image",
            width=400
        )


        image_result = predict_image(image)



    # NLP processing
    if description.strip():

        text_result = predict_text(
            description
        )



    # Fusion decision
    final_result = combine(
        image_result=image_result,
        text_result=text_result
    )


    st.divider()

    st.subheader("Prediction Result")


    st.success(
        f"Category: {final_result['category']}"
    )


    st.info(
        f"Confidence: {final_result['confidence']}%"
    )


    st.write(
        "Prediction Source:",
        final_result["source"]
    )