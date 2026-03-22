This notebook collects example tool catalogs and example workflow tasks used to demonstrate `workflow_auto_assembler` in action.

The examples are intentionally synthetic. Their purpose is to show how WAA assembles typed linear workflows from available tool schemas, not to claim broad real-world agent capability.


### Example functions


A set of 24 simple mock functions was defined alongside explicit input and output models. Together they form the available tool catalog from which WAA assembles workflows.

<details>

```python
class TranslateTextInput(BaseModel):
    text: str = Field(..., description="Text to translate.")
    target_language: str = Field(..., description="Target language code.")

class TranslateTextOutput(BaseModel):
    translated_text: str = Field(..., description="Text translated into the target language.")

def translate_text(inputs: TranslateTextInput) -> TranslateTextOutput:
    """Translate text to another language."""
    return TranslateTextOutput(
        translated_text=f"Translated({inputs.text}) → {inputs.target_language}"
    )
```

```python
class SummarizeTextInput(BaseModel):
    content: str = Field(..., description="Text to summarize.")

class SummarizeTextOutput(BaseModel):
    summary: str = Field(..., description="Short summarized version of the content.")

def summarize_text(inputs: SummarizeTextInput) -> SummarizeTextOutput:
    """Summarize long content."""
    return SummarizeTextOutput(summary="Short summary...")
```

```python
class DetectSentimentInput(BaseModel):
    text: str

class DetectSentimentOutput(BaseModel):
    sentiment: str
    score: float

def detect_sentiment(inputs: DetectSentimentInput) -> DetectSentimentOutput:
    """Detect sentiment of given text."""
    return DetectSentimentOutput(sentiment="positive", score=0.9)
```

```python
class ExtractKeywordsInput(BaseModel):
    text: str

class ExtractKeywordsOutput(BaseModel):
    keywords: List[str]

def extract_keywords(inputs: ExtractKeywordsInput) -> ExtractKeywordsOutput:
    """Extract keywords."""
    return ExtractKeywordsOutput(keywords=["keyword1", "keyword2"])
```

```python
class ConvertUnitsInput(BaseModel):
    value: float
    from_unit: str
    to_unit: str

class ConvertUnitsOutput(BaseModel):
    converted_value: float

def convert_units(inputs: ConvertUnitsInput) -> ConvertUnitsOutput:
    """Convert measurement units."""
    return ConvertUnitsOutput(converted_value=inputs.value * 1.3)
```

```python
class CalculateDistanceInput(BaseModel):
    lat1: float
    lon1: float
    lat2: float
    lon2: float

class CalculateDistanceOutput(BaseModel):
    distance_km: float

def calculate_distance(inputs: CalculateDistanceInput) -> CalculateDistanceOutput:
    """Calculate distance."""
    return CalculateDistanceOutput(distance_km=42.0)
```

```python
class GeneratePlotInput(BaseModel):
    data: List[float]
    title: str

class GeneratePlotOutput(BaseModel):
    image_path: str

def generate_plot(inputs: GeneratePlotInput) -> GeneratePlotOutput:
    """Generate plot."""
    return GeneratePlotOutput(image_path="/tmp/plot.png")
```

```python
class CurrencyExchangeInput(BaseModel):
    amount: float
    from_currency: str
    to_currency: str

class CurrencyExchangeOutput(BaseModel):
    converted_amount: float

def currency_exchange(inputs: CurrencyExchangeInput) -> CurrencyExchangeOutput:
    """Convert currencies."""
    return CurrencyExchangeOutput(converted_amount=inputs.amount * 1.1)
```

```python
class StoreFileInput(BaseModel):
    filename: str
    content: str

class StoreFileOutput(BaseModel):
    storage_path: str

def store_file(inputs: StoreFileInput) -> StoreFileOutput:
    """Store file."""
    return StoreFileOutput(storage_path=f"/tmp/{inputs.filename}")
```

```python
class LoadFileInput(BaseModel):
    path: str

class LoadFileOutput(BaseModel):
    content: str

def load_file(inputs: LoadFileInput) -> LoadFileOutput:
    """Load file from storage."""
    return LoadFileOutput(content="Loaded file contents...")
```

```python
class SendSMSInput(BaseModel):
    phone: str
    message: str

class SendSMSOutput(BaseModel):
    success: bool

def send_sms(inputs: SendSMSInput) -> SendSMSOutput:
    """Send SMS."""
    return SendSMSOutput(success=True)
```

```python
class DetectObjectsInput(BaseModel):
    image_path: str

class DetectObjectsOutput(BaseModel):
    objects: List[str]

def detect_objects(inputs: DetectObjectsInput) -> DetectObjectsOutput:
    """Detect objects in image."""
    return DetectObjectsOutput(objects=["cat", "chair"])
```

```python
class TranscribeAudioInput(BaseModel):
    audio_path: str

class TranscribeAudioOutput(BaseModel):
    text: str

def transcribe_audio(inputs: TranscribeAudioInput) -> TranscribeAudioOutput:
    """Transcribe audio file."""
    return TranscribeAudioOutput(text="Transcribed text")
```

```python
class GenerateReportInput(BaseModel):
    title: str
    body: str

class GenerateReportOutput(BaseModel):
    pdf_path: str

def generate_report(inputs: GenerateReportInput) -> GenerateReportOutput:
    """Generate report."""
    return GenerateReportOutput(pdf_path="/tmp/report.pdf")
```

```python
class LookupCoordinatesInput(BaseModel):
    city: str

class LookupCoordinatesOutput(BaseModel):
    lat: float
    lon: float

def lookup_coordinates(inputs: LookupCoordinatesInput) -> LookupCoordinatesOutput:
    """Lookup coordinates."""
    return LookupCoordinatesOutput(lat=10.0, lon=20.0)
```

```python
class CheckAvailabilityInput(BaseModel):
    item_id: str
    location: str

class CheckAvailabilityOutput(BaseModel):
    available: bool
    stock: int

def check_availability(inputs: CheckAvailabilityInput) -> CheckAvailabilityOutput:
    """Check stock."""
    return CheckAvailabilityOutput(available=True, stock=5)
```

```python
class CreateOrderInput(BaseModel):
    item_id: str
    quantity: int

class CreateOrderOutput(BaseModel):
    order_id: str
    status: str

def create_order(inputs: CreateOrderInput) -> CreateOrderOutput:
    """Create order."""
    return CreateOrderOutput(order_id="ORD-001", status="created")
```

```python
class CheckOrderStatusInput(BaseModel):
    order_id: str

class CheckOrderStatusOutput(BaseModel):
    status: str

def check_order_status(inputs: CheckOrderStatusInput) -> CheckOrderStatusOutput:
    """Check order status."""
    return CheckOrderStatusOutput(status="in progress")
```

```python
class UploadImageInput(BaseModel):
    image_path: str
    label: str

class UploadImageOutput(BaseModel):
    success: bool
    url: str

def upload_image(inputs: UploadImageInput) -> UploadImageOutput:
    """Upload image."""
    return UploadImageOutput(success=True, url="http://img.local")
```

```python
class RewriteTextInput(BaseModel):
    text: str
    tone: str

class RewriteTextOutput(BaseModel):
    rewritten: str

def rewrite_text(inputs: RewriteTextInput) -> RewriteTextOutput:
    """Rewrite text in specified tone."""
    return RewriteTextOutput(rewritten=f"{inputs.tone} version of {inputs.text}")
```

```python
class GetWeatherInput(BaseModel):
    city: str = Field(..., description="Name of the city for which weather to be extracted.")

class GetWeatherOutput(BaseModel):
    condition: str = Field(..., description="Weather condition in the requested city.")
    temperature: float = Field(..., description="Termperature in C in the requested city.")
    humidity: float = Field(None, description="Name of the city for which weather to be extracted.")

def get_weather(inputs: GetWeatherInput) -> GetWeatherOutput:
    """Get the current weather for a city from weather forcast api."""
    return GetWeatherOutput(
        condition = "Sunny",
        temperature = 20,
        humidity = 0.6
    )
```

```python
class EmailInformationPoint(BaseModel):
    title: str = Field(None, description="Few word description of the information.")
    content: str = Field(..., description="Content of the information.")

class SendReportEmailInput(BaseModel):
    city: str = Field(..., description="Name of the city where report will be send.")
    information: list[EmailInformationPoint]

class SendReportEmailOutput(BaseModel):
    email_sent: bool = Field(..., description="Conformation that email was send successfully.")
    message: str = Field(None, description="Optional comments from the process.")

def send_report_email(inputs: SendReportEmailInput) -> SendReportEmailOutput:
    """Sends a report email with given information points to a city."""
    return SendReportEmailOutput(
        email_sent = True,
        message = "Email sent to city of your choosing!"
    )
```

```python
class QueryDatabaseInput(BaseModel):
    topic: str = Field(..., description="Topic of a requested piece of information.")
    location: str = Field(None, description="Filter for location name.")
    uid: str = Field(None, description="Filter for unique indentifier of the database item.")

class QueryDatabaseOutput(BaseModel):
    info: str = Field(..., description="Content of the information.")
    uid: str = Field(None, description="Unique indentifier of the database item.")

def query_database(inputs : QueryDatabaseInput) -> QueryDatabaseOutput:
    """Get information from the database with provided filters."""
    return QueryDatabaseOutput(
        info = "Content extracted from the database for your query is ...",
        uid = "0000"
    )
```

```python
class QueryWebInput(BaseModel):
    search_input: str = Field(..., description="Topic to be searched on the web.")


class QueryWebOutput(BaseModel):
    search_results: List[str] = Field(..., description="List relevant info from search results.")


def query_web(inputs : QueryWebInput) -> QueryWebOutput:
    """Get information from the internet for provided query."""
    return QueryWebOutput(
        search_results = ["Relevant content found in first search result is ..."],
    )

```

</details>

### Example tasks

To test schema-first planning, 25 workflow tasks were defined through a description plus target input and output models. These tasks were used during development and can serve as templates for creating new benchmark or demo tasks.

#### 1. Translate to French


<details>

```python

class Task1Input(BaseModel):
    text: str = Field(..., description="Text to translate.")
    target_language: str = Field(..., description="Target language code (e.g., 'fr').")

class Task1Output(BaseModel):
    translated_text: str = Field(..., description="Translated text.")

task_specs['task_1'] = {
        "description": "Translate a sentence into French.",
        "input_model": Task1Input,
        "output_model": Task1Output,
}

t1_inputs = [
    Task1Input(text=t, target_language=lang)
    for t, lang in [
        ("Hello", "fr"), ("Good morning", "es"), ("How are you?", "de"),
        ("See you soon", "it"), ("Thank you", "pl"), ("Where is the station?", "ja"),
        ("Nice to meet you", "ko"), ("I need help", "pt"), ("What time is it?", "ar"),
        ("Good night", "nl"),
    ]
]
t1_outputs = [
    Task1Output(translated_text=f"Translated({i.text}) → {i.target_language}") for i in t1_inputs
]

```

</details>


#### 2. Summarize Document


<details>

```python

class Task2Input(BaseModel):
    content: str = Field(..., description="Text to summarize.")

class Task2Output(BaseModel):
    summary: str = Field(..., description="Short summary of content.")

task_specs['task_2'] = {
        "description": "Summarize a document and return the summary.",
        "input_model": Task2Input,
        "output_model": Task2Output,
}

t2_inputs = [Task2Input(content=f"Long text example #{i} ...") for i in range(1, 11)]
t2_outputs = [Task2Output(summary="Short summary...") for _ in t2_inputs]

```

</details>


#### 3. Sentiment + Keywords


<details>

```python

class Task3Input(BaseModel):
    text: str = Field(..., description="Text to analyze.")

class Task3Output(BaseModel):
    sentiment: str = Field(..., description="Detected sentiment label.")
    score: float = Field(..., description="Confidence score 0-1.")
    keywords: List[str] = Field(..., description="Extracted keywords.")

task_specs['task_3'] = {
        "description": "Detect sentiment of text and extract keywords.",
        "input_model": Task3Input,
        "output_model": Task3Output,
    }


t3_inputs = [
    Task3Input(text=txt) for txt in [
        "I love this product!", "This is terrible.", "It's okay, I guess.",
        "Absolutely fantastic!", "Very disappointing.", "Mixed feelings overall.",
        "Exceeded expectations!", "Not worth the price.", "Pretty decent", "Amazing value!"
    ]
]
t3_outputs = [
    Task3Output(sentiment="positive", score=0.9, keywords=["keyword1", "keyword2"]) for _ in t3_inputs
]

```

</details>


#### 4. Convert Units + SMS

<details>

```python

class Task4Input(BaseModel):
    value: float = Field(..., description="Numeric value to convert.")
    from_unit: str = Field(..., description="Source unit (e.g., 'C').")
    to_unit: str = Field(..., description="Target unit (e.g., 'F').")
    phone: str = Field(..., description="Phone number to receive SMS.")

class Task4Output(BaseModel):
    converted_value: float = Field(..., description="Converted numeric value.")
    sms_sent: bool = Field(..., description="Whether SMS was sent.")

task_specs['task_4'] = {
        "description": "Convert temperature units and send SMS with results.",
        "input_model": Task4Input,
        "output_model": Task4Output,
    }

t4_inputs = [
    Task4Input(value=v, from_unit="C", to_unit="F", phone=f"+15550000{i:02d}")
    for i, v in enumerate([0, 5, 10, 12.5, 15, 18, 20, 25, 30, 37], start=1)
]
# convert_units mock = value * 1.3 ; send_sms mock = True
t4_outputs = [
    Task4Output(converted_value=round(i.value * 1.3, 6), sms_sent=True) for i in t4_inputs
]

```

</details>


#### 5. Weather Report

<details>

```python

class Task5Input(BaseModel):
    city: str = Field(..., description="City name.")
    report_title: Optional[str] = Field("City Weather Report", description="Title for the report.")

class Task5Output(BaseModel):
    report_pdf_path: str = Field(..., description="Path to generated report PDF.")
    weather_condition: str = Field(..., description="Weather condition.")
    temperature_c: float = Field(..., description="Temperature in Celsius.")
    lat: float = Field(..., description="Latitude of city.")
    lon: float = Field(..., description="Longitude of city.")

task_specs['task_5'] = {
        "description": "Lookup city coordinates, get weather, summarize into a report.",
        "input_model": Task5Input,
        "output_model": Task5Output,
    }

t5_inputs = [
    Task5Input(city=c, report_title=f"{c} Weather Report")
    for c in ["Paris", "Berlin", "Warsaw", "Tokyo", "Sydney", "New York", "London", "Toronto", "Lisbon", "Rome"]
]
# get_weather mock => Sunny, 20.0 ; lookup_coordinates mock => 10.0, 20.0 ; report path fixed
t5_outputs = [
    Task5Output(
        report_pdf_path="/tmp/report.pdf",
        weather_condition="Sunny",
        temperature_c=20.0,
        lat=10.0,
        lon=20.0,
    ) for _ in t5_inputs
]

```

</details>


#### 6. DB Query + Translate + Upload


<details>

```python

class Task6Input(BaseModel):
    topic: str = Field(..., description="Database topic to query.")
    target_language: str = Field(..., description="Language code for translation.")
    image_path: str = Field(..., description="Path of related image to upload.")
    label: str = Field(..., description="Label for the image upload.")

class Task6Output(BaseModel):
    translated_info: str = Field(..., description="Translated DB info.")
    uid: str = Field(..., description="Database item UID.")
    image_url: str = Field(..., description="URL of uploaded image.")


task_specs['task_6'] = {
        "description": "Query database, translate results, upload image of related doc.",
        "input_model": Task6Input,
        "output_model": Task6Output,
    }

t6_inputs = [
    Task6Input(topic=topic, target_language=lang, image_path=f"/images/{i}.png", label=f"doc-{i}")
    for i, (topic, lang) in enumerate([
        ("birds", "fr"), ("finance", "es"), ("weather", "de"), ("transport", "it"),
        ("education", "pl"), ("sports", "ja"), ("technology", "ko"), ("health", "pt"),
        ("energy", "ar"), ("tourism", "nl")
    ], start=1)
]
# query_database => uid="0000" ; translate_text => "Translated(...)" (but we expose final as paraphrase)
# upload_image => url fixed
t6_outputs = [
    Task6Output(
        translated_info=f"Translated(Content extracted from the database for your query is ...) → {lang}",
        uid="0000",
        image_url="http://img.local",
    ) for _, (_, lang) in enumerate([
        ("birds", "fr"), ("finance", "es"), ("weather", "de"), ("transport", "it"),
        ("education", "pl"), ("sports", "ja"), ("technology", "ko"), ("health", "pt"),
        ("energy", "ar"), ("tourism", "nl")
    ], start=1)
]

```

</details>


#### 7. Transcribe + Summarize

<details>

```python

class Task7Input(BaseModel):
    audio_path: str = Field(..., description="Path to meeting audio file.")

class Task7Output(BaseModel):
    transcript: str = Field(..., description="Transcribed text.")
    summary: str = Field(..., description="Summary of transcript.")
    sentiment: str = Field(..., description="Overall sentiment label.")
    score: float = Field(..., description="Confidence score 0-1.")

task_specs['task_7'] = {
        "description": "Transcribe meeting audio, summarize notes, detect sentiment.",
        "input_model": Task7Input,
        "output_model": Task7Output,
    }

t7_inputs = [Task7Input(audio_path=f"/audio/meeting_{i}.wav") for i in range(1, 11)]
t7_outputs = [
    Task7Output(transcript="Transcribed text", summary="Short summary...", sentiment="positive", score=0.9)
    for _ in t7_inputs
]

```

</details>


#### 8. Weather + Convert + PDF

<details>

```python

class Task8Input(BaseModel):
    city: str = Field(..., description="City for weather.")
    to_unit: str = Field("F", description="Target unit for temperature (e.g., 'F').")
    report_title: Optional[str] = Field("Weather Report", description="Report title.")

class Task8Output(BaseModel):
    report_pdf_path: str = Field(..., description="PDF path for report.")
    temperature_converted: float = Field(..., description="Converted temperature.")
    condition: str = Field(..., description="Weather condition.")

task_specs['task_8'] = {
        "description": "Get weather, convert units to Fahrenheit, generate report PDF.",
        "input_model": Task8Input,
        "output_model": Task8Output,
    }

t8_inputs = [
    Task8Input(city=c, to_unit="F", report_title=f"{c} Weather Report")
    for c in ["Paris", "Berlin", "Warsaw", "Tokyo", "Sydney", "NYC", "London", "Toronto", "Lisbon", "Rome"]
]
# get_weather temp=20 ; convert_units => 20*1.3=26.0 ; report path fixed
t8_outputs = [
    Task8Output(report_pdf_path="/tmp/report.pdf", temperature_converted=26.0, condition="Sunny")
    for _ in t8_inputs
]

```

</details>


#### 9. Web Search + Rewrite

<details>

```python

class Task9Input(BaseModel):
    search_input: str = Field(..., description="Web search query.")
    tone: str = Field("formal", description="Target tone for rewriting.")

class Task9Output(BaseModel):
    keywords: List[str] = Field(..., description="Extracted keywords.")
    rewritten: str = Field(..., description="Rewritten text in requested tone.")
    sources: List[str] = Field(..., description="List of source snippets/links.")

task_specs['task_9'] = {
        "description": "Query web, extract keywords, rewrite text to formal tone.",
        "input_model": Task9Input,
        "output_model": Task9Output,
    }

t9_inputs = [
    Task9Input(search_input=q, tone=tone)
    for q, tone in [
        ("latest AI news", "formal"), ("travel tips Japan", "neutral"), ("healthy recipes", "friendly"),
        ("best running shoes 2025", "concise"), ("python decorators", "technical"),
        ("sql vs nosql", "balanced"), ("renewable energy facts", "informative"),
        ("quantum computing basics", "simple"), ("cloud cost optimization", "professional"),
        ("mlops pipelines", "succinct"),
    ]
]
# extract_keywords const ; summarize const ; rewrite_text => f"{tone} version of Short summary..."
t9_outputs = [
    Task9Output(
        keywords=["keyword1", "keyword2"],
        rewritten=f"{i.tone} version of {i.search_input}",
        sources=["Relevant content found in first search result is ..."],
    ) for i in t9_inputs
]

```

</details>


#### 10. Image Objects + Email

<details>

```python

class Task10Input(BaseModel):
    image_path: str = Field(..., description="Path to image file.")
    city: str = Field(..., description="City where email should be sent.")
    title: Optional[str] = Field("Photo Analysis", description="Email title.")

class Task10Output(BaseModel):
    objects: List[str] = Field(..., description="Detected objects in image.")
    email_sent: bool = Field(..., description="Whether the email was sent.")
    message: Optional[str] = Field(None, description="Email send message.")

task_specs['task_10'] = {
        "description": "Detect objects in photo, generate short summary text, send email, leave message.",
        "input_model": Task10Input,
        "output_model": Task10Output,
    }

t10_inputs = [
    Task10Input(image_path=f"/img/photo_{i}.jpg", city=c, title="Photo Analysis")
    for i, c in enumerate(["Paris","Berlin","Warsaw","Tokyo","Sydney","NYC","London","Toronto","Lisbon","Rome"], 1)
]
t10_outputs = [
    Task10Output(objects=["cat", "chair"], email_sent=True, message="Email sent to city of your choosing!")
    for _ in t10_inputs
]

```

</details>


#### 11. Distance + Currency + SMS


<details>

```python

class Task11Input(BaseModel):
    lat1: float
    lon1: float
    lat2: float
    lon2: float
    amount: float = Field(..., description="Amount to convert for ticket.")
    from_currency: str
    to_currency: str
    phone: str

class Task11Output(BaseModel):
    distance_km: float
    converted_amount: float
    sms_sent: bool

task_specs['task_11'] = {
        "description": "Calculate distance between cities, convert currency for ticket, send SMS.",
        "input_model": Task11Input,
        "output_model": Task11Output,
    }

t11_inputs = [
    Task11Input(
        lat1=52.2297, lon1=21.0122, lat2=48.8566, lon2=2.3522,
        amount=amt, from_currency="USD", to_currency="EUR", phone=f"+1555011{i:02d}"
    )
    for i, amt in enumerate([10, 20, 35, 50, 75, 100, 125.5, 200, 350, 500], 1)
]
# calculate_distance => 42 ; currency_exchange => amount*1.1 ; sms True
t11_outputs = [
    Task11Output(distance_km=42.0, converted_amount=round(i.amount * 1.1, 6), sms_sent=True)
    for i in t11_inputs
]

```

</details>


#### 12. Summarize File + Email

<details>

```python

class Task12Input(BaseModel):
    path: str = Field(..., description="Path of text file to load.")
    out_filename: str = Field(..., description="Filename for stored summary.")
    city: str = Field(..., description="City where notification email is sent.")

class Task12Output(BaseModel):
    stored_path: str = Field(..., description="Path to stored summary file.")
    summary: str = Field(..., description="Summary content.")
    email_sent: bool = Field(..., description="Whether email was sent.")

task_specs['task_12'] = {
        "description": "Load text file, summarize, store summary as new file, email notification.",
        "input_model": Task12Input,
        "output_model": Task12Output,
    }

t12_inputs = [
    Task12Input(path=f"/docs/file_{i}.txt", out_filename=f"summary_{i}.txt", city=c)
    for i, c in enumerate(["Paris","Berlin","Warsaw","Tokyo","Sydney","NYC","London","Toronto","Lisbon","Rome"], 1)
]
# load_file => content ignored; summarize const; store_file => /tmp/{out_filename}; email True
t12_outputs = [
    Task12Output(stored_path=f"/tmp/{i.out_filename}", summary="Short summary...", email_sent=True)
    for i in t12_inputs
]

```

</details>


#### 13. DB Stock + Order + Email

<details>

```python

class Task13Input(BaseModel):
    topic: str = Field(..., description="Topic to query from DB.")
    item_id: str = Field(..., description="Item identifier for stock/order.")
    quantity: int = Field(..., description="Order quantity.")
    location: str = Field(..., description="Stock location.")
    city: str = Field(..., description="City for confirmation email.")

class Task13Output(BaseModel):
    available: bool
    stock: int
    order_id: str
    status: str
    email_sent: bool

task_specs['task_13'] = {
        "description": "Query database, check stock availability, create order, confirm email.",
        "input_model": Task13Input,
        "output_model": Task13Output,
    }


t13_inputs = [
    Task13Input(
        topic=tpc, item_id=f"SKU-{1000+i}", quantity=q, location=loc, city=city
    )
    for i, (tpc, q, loc, city) in enumerate([
        ("laptops",1,"WH-A","Paris"), ("monitors",2,"WH-B","Berlin"), ("keyboards",5,"WH-A","Warsaw"),
        ("mice",3,"WH-C","Tokyo"), ("chairs",1,"WH-D","Sydney"), ("desks",2,"WH-A","NYC"),
        ("hubs",4,"WH-B","London"), ("cables",10,"WH-C","Toronto"), ("routers",2,"WH-A","Lisbon"),
        ("ssd",3,"WH-D","Rome")
    ], 1)
]
# check_availability => available=True, stock=5; create_order => ORD-001, created; email True
t13_outputs = [
    Task13Output(available=True, stock=5, order_id="ORD-001", status="created", email_sent=True)
    for _ in t13_inputs
]

```

</details>


#### 14. Distance Plot

<details>

```python

class Task14Input(BaseModel):
    city_a: str = Field(..., description="First city.")
    city_b: str = Field(..., description="Second city.")
    title: str = Field("Distance Plot", description="Plot title.")

class Task14Output(BaseModel):
    distance_km: float
    plot_path: str
    lat_a: float
    lon_a: float
    lat_b: float
    lon_b: float

task_specs['task_14'] = {
        "description": "Lookup coordinates, calculate distance, generate map plot, send to web.",
        "input_model": Task14Input,
        "output_model": Task14Output,
    }

t14_inputs = [
    Task14Input(city_a=a, city_b=b, title="Distance Plot")
    for a, b in [
        ("Warsaw","Paris"), ("Berlin","London"), ("Tokyo","Seoul"), ("NYC","Boston"), ("LA","SF"),
        ("Sydney","Melbourne"), ("Toronto","Montreal"), ("Lisbon","Madrid"), ("Rome","Milan"), ("Prague","Vienna")
    ]
]
t14_outputs = [
    Task14Output(distance_km=42.0, plot_path="/tmp/plot.png",
                 lat_a=10.0, lon_a=20.0, lat_b=10.0, lon_b=20.0)
    for _ in t14_inputs
]

```

</details>


#### 15. Web Sentiment Summary

<details>

```python

class Task15Input(BaseModel):
    search_input: str = Field(..., description="Query for web search.")
    rewrite_tone: str = Field("concise", description="Tone for rewritten text.")

class Task15Output(BaseModel):
    summary: str
    sentiment: str
    score: float
    keywords: List[str]
    rewritten: str
    sources: List[str]

task_specs['task_15'] = {
        "description": "Query web, detect sentiment, extract keywords, summarize, rewrite.",
        "input_model": Task15Input,
        "output_model": Task15Output,
    }

t15_inputs = [
    Task15Input(search_input=q, rewrite_tone=tone)
    for q, tone in [
        ("compare llms", "concise"), ("fastapi vs flask", "neutral"), ("docker best practices", "professional"),
        ("kubernetes basics", "simple"), ("vector databases", "technical"), ("retrieval augmented generation", "formal"),
        ("prompt engineering tips", "friendly"), ("gpu optimization", "succinct"), ("pydantic v2 changes", "informative"),
        ("langchain vs llamaindex", "balanced"),
    ]
]
t15_outputs = [
    Task15Output(
        summary="Short summary...", sentiment="positive", score=0.9,
        keywords=["keyword1", "keyword2"],
        rewritten=f"{i.rewrite_tone} version of Short summary...",
        sources=["Result 1","Result 2"],
    )
    for i in t15_inputs
]

```

</details>


#### 16. Weather + Audio + Report


<details>

```python

class Task16Input(BaseModel):
    city: str = Field(..., description="City name.")
    audio_path: str = Field(..., description="Path to instructions audio.")
    report_title: str = Field("City Ops Report", description="Report title.")

class Task16Output(BaseModel):
    pdf_path: str
    email_sent: bool
    transcript: str
    condition: str
    temperature_c: float
    lat: float
    lon: float

task_specs['task_16'] = {
        "description": "Get weather, lookup coordinates, transcribe audio instructions, generate report, send email.",
        "input_model": Task16Input,
        "output_model": Task16Output,
    }

t16_inputs = [
    Task16Input(city=c, audio_path=f"/audio/instructions_{i}.wav", report_title="City Ops Report")
    for i, c in enumerate(["Paris","Berlin","Warsaw","Tokyo","Sydney","NYC","London","Toronto","Lisbon","Rome"], 1)
]
t16_outputs = [
    Task16Output(pdf_path="/tmp/report.pdf", email_sent=True, transcript="Transcribed text",
                 condition="Sunny", temperature_c=20.0, lat=10.0, lon=20.0)
    for _ in t16_inputs
]

```

</details>


#### 17. DB + Distance + Report

<details>

```python

class Task17Input(BaseModel):
    topic: str = Field(..., description="DB topic to query.")
    lat1: float
    lon1: float
    lat2: float
    lon2: float
    image_path: str
    label: str
    phone: str
    report_title: str = Field("DB+Distance Report", description="Report title.")

class Task17Output(BaseModel):
    report_pdf_path: str
    image_url: str
    distance_km: float
    sms_sent: bool
    uid: str

task_specs['task_17'] = {
        "description": "Query database, calculate distance, generate PDF report, upload image, send SMS results.",
        "input_model": Task17Input,
        "output_model": Task17Output,
    }

t17_inputs = [
    Task17Input(
        topic="infrastructure",
        lat1=52.2297, lon1=21.0122, lat2=48.8566, lon2=2.3522,
        image_path=f"/img/{i}.png", label=f"case-{i}", phone=f"+1555017{i:02d}",
        report_title="DB+Distance Report"
    )
    for i in range(1, 11)
]
t17_outputs = [
    Task17Output(report_pdf_path="/tmp/report.pdf", image_url="http://img.local",
                 distance_km=42.0, sms_sent=True, uid="0000")
    for _ in t17_inputs
]

```

</details>


#### 18. Call Summary + Order

<details>

```python

class Task18Input(BaseModel):
    audio_path: str
    item_id: str
    quantity: int
    city: str = Field(..., description="City for email notification.")
    out_filename: str = Field("call_summary.txt", description="Filename to store summary.")

class Task18Output(BaseModel):
    transcript: str
    sentiment: str
    score: float
    stored_path: str
    order_id: str
    order_status: str
    email_sent: bool

task_specs['task_18'] = {
        "description": "Transcribe call audio, detect sentiment, store summary, create order, check status, send email.",
        "input_model": Task18Input,
        "output_model": Task18Output,
    }

t18_inputs = [
    Task18Input(
        audio_path=f"/audio/call_{i}.wav", item_id=f"SKU-{2000+i}", quantity=(i % 5) + 1,
        city=c, out_filename=f"call_summary_{i}.txt"
    )
    for i, c in enumerate(["Paris","Berlin","Warsaw","Tokyo","Sydney","NYC","London","Toronto","Lisbon","Rome"], 1)
]
t18_outputs = [
    Task18Output(transcript="Transcribed text", sentiment="positive", score=0.9,
                 stored_path=f"/tmp/{i.out_filename}", order_id="ORD-001",
                 order_status="in progress", email_sent=True)
    for i in t18_inputs
]

```

</details>


#### 19. Web Summary + Report

<details>

```python

class Task19Input(BaseModel):
    search_input: str
    rewrite_tone: str = Field("formal", description="Tone for rewritten copy.")
    amount: float
    from_currency: str
    to_currency: str
    report_title: str = Field("Web Findings Report", description="Report title.")
    phone: str

class Task19Output(BaseModel):
    report_pdf_path: str
    rewritten: str
    converted_amount: float
    summary: str
    sms_sent: bool
    sources: List[str]

task_specs['task_19'] = {
        "description": "Query web, summarize results, rewrite text, convert currency estimate, generate report, send SMS.",
        "input_model": Task19Input,
        "output_model": Task19Output,
    }

t19_inputs = [
    Task19Input(
        search_input=q, rewrite_tone="formal", amount=amt,
        from_currency="USD", to_currency="EUR", report_title="Web Findings Report", phone=f"+1555019{i:02d}"
    )
    for i, (q, amt) in enumerate([
        ("ai news",10), ("best laptops",25), ("learn python",50), ("k8s tutorial",75), ("docker tips",100),
        ("mlops guide",125), ("git workflows",150), ("fastapi examples",200), ("sql tuning",300), ("cloud costs",500)
    ], 1)
]
t19_outputs = [
    Task19Output(
        report_pdf_path="/tmp/report.pdf", rewritten="formal version of Short summary...",
        converted_amount=round(i.amount * 1.1, 6), summary="Short summary...", sms_sent=True,
        sources=["Result 1","Result 2"]
    )
    for i in t19_inputs
]

```

</details>


#### 20. Full Pipeline Showcase


<details>

```python

class Task20Input(BaseModel):
    db_topic: str = Field(..., description="Topic for DB query.")
    web_query: str = Field(..., description="Query for web search.")
    city: str = Field(..., description="City for weather and email.")
    units_to: str = Field("F", description="Target unit for temperature.")
    lat1: float
    lon1: float
    lat2: float
    lon2: float
    plot_title: str = Field("Route Distance", description="Plot title.")
    file_name: str = Field("summary.txt", description="Filename for stored summary.")
    image_path: str
    image_label: str
    item_id: str
    quantity: int
    phone: str
    report_title: str = Field("Comprehensive Report", description="Report title.")
    rewrite_tone: str = Field("professional", description="Tone for rewritten text.")

class Task20Output(BaseModel):
    keywords: List[str]
    summary: str
    sentiment: str
    score: float
    rewritten: str
    lat: float
    lon: float
    condition: str
    temperature_converted: float
    distance_km: float
    plot_path: str
    report_pdf_path: str
    stored_path: str
    loaded_content: str
    image_url: str
    order_id: str
    order_status: str
    sms_sent: bool
    email_sent: bool
    db_uid: str

task_specs['task_20'] = {
        "description": (
            "Query database → query web → extract keywords → summarize → detect sentiment → rewrite → "
            "lookup coordinates → get weather → convert units → calculate distance → create plot → generate "
            "report → store file → load file → upload image → create order → check status → send SMS → "
            "send email → save summary to DB."
        ),
        "input_model": Task20Input,
        "output_model": Task20Output,
    }

t20_inputs = [
    Task20Input(
        db_topic="urban planning",
        web_query=f"transport trends {2020+i}",
        city=c,
        units_to="F",
        lat1=52.2297, lon1=21.0122, lat2=48.8566, lon2=2.3522,
        plot_title="Route Distance",
        file_name=f"summary_{i}.txt",
        image_path=f"/img/mega_{i}.png",
        image_label=f"mega-{i}",
        item_id=f"SKU-MEGA-{i}",
        quantity=(i % 5) + 1,
        phone=f"+1555020{i:02d}",
        report_title="Comprehensive Report",
        rewrite_tone="professional",
    )
    for i, c in enumerate(["Paris","Berlin","Warsaw","Tokyo","Sydney","NYC","London","Toronto","Lisbon","Rome"], 1)
]
t20_outputs = [
    Task20Output(
        keywords=["keyword1","keyword2"], summary="Short summary...", sentiment="positive", score=0.9,
        rewritten="professional version of Short summary...", lat=10.0, lon=20.0, condition="Sunny",
        temperature_converted=26.0, distance_km=42.0, plot_path="/tmp/plot.png",
        report_pdf_path="/tmp/report.pdf", stored_path=f"/tmp/{i.file_name}",
        loaded_content="Loaded file contents...", image_url="http://img.local",
        order_id="ORD-001", order_status="in progress", sms_sent=True, email_sent=True, db_uid="0000"
    )
    for i in t20_inputs
]

```

</details>


> Note: Tasks 21–25 are examples that should **not** work with the provided example tools list.

#### 21. DB Summary + Notify

<details>

```python

class Task21Input(BaseModel):
    db_topic: str = Field(..., description="Topic for DB query.")
    phone: str = Field(..., description="Phone number to notify.")
    report_title: str = Field("Summary Report", description="Report title.")
    city: str = Field("Berlin", description="City for report email.")

class Task21Output(BaseModel):
    summary: str
    sms_sent: bool
    email_sent: bool
    db_uid: str
    db_write_uid: str


task_specs['task_21'] = {
        "description": (
            "Query database -> summarize -> send SMS -> send email -> save summary to DB."
        ),
        "input_model": Task21Input,
        "output_model": Task21Output,
    }

t21_inputs = [
    Task21Input(db_topic=f"topic-{i}", phone=f"+1555000{i:02d}")
    for i in range(1, 6)
]

t21_outputs = [
    Task21Output(
        summary="Short summary...",
        sms_sent=True,
        email_sent=True,
        db_uid="0000",
        db_write_uid="WRITE-0000",
    ) for _ in t21_inputs
]


```

</details>


#### 22. OCR Image


<details>

```python

class Task22Input(BaseModel):
    image_path: str
    label: str

class Task22Output(BaseModel):
    ocr_text: str
    image_url: str


task_specs['task_22'] = {
        "description": (
            "Upload image -> extract text from image (OCR)."
        ),
        "input_model": Task22Input,
        "output_model": Task22Output,
    }

t22_inputs = [
    Task22Input(image_path=f"/img/doc_{i}.png", label=f"doc-{i}")
    for i in range(1, 6)
]

t22_outputs = [
    Task22Output(
        ocr_text="Detected text...",
        image_url="http://img.local",
    ) for _ in t22_inputs
]


```

</details>


#### 23. Embedding + Index


<details>

```python

class Task23Input(BaseModel):
    text: str
    top_k: int = Field(5, description="Number of nearest neighbors.")

class Task23Output(BaseModel):
    embedding: List[float]
    index_id: str


task_specs['task_23'] = {
        "description": (
            "Generate embedding -> store in vector index -> return index id."
        ),
        "input_model": Task23Input,
        "output_model": Task23Output,
    }

t23_inputs = [
    Task23Input(text=f"sample text {i}")
    for i in range(1, 6)
]

t23_outputs = [
    Task23Output(
        embedding=[0.1, 0.2, 0.3],
        index_id="vec-0000",
    ) for _ in t23_inputs
]


```

</details>


#### 24. Contract Compliance


<details>

```python

class Task24Input(BaseModel):
    contract_text: str
    region: str = Field("EU", description="Compliance region.")

class Task24Output(BaseModel):
    compliance_report: str
    risk_score: float


task_specs['task_24'] = {
        "description": (
            "Analyze contract -> run compliance check -> return report and risk score."
        ),
        "input_model": Task24Input,
        "output_model": Task24Output,
    }

t24_inputs = [
    Task24Input(contract_text=f"contract text {i}")
    for i in range(1, 6)
]

t24_outputs = [
    Task24Output(
        compliance_report="No issues found.",
        risk_score=0.1,
    ) for _ in t24_inputs
]


```

</details>


#### 25. Crypto Transfer


<details>

```python

class Task25Input(BaseModel):
    wallet_from: str
    wallet_to: str
    amount: float

class Task25Output(BaseModel):
    tx_hash: str
    receipt_url: str


task_specs['task_25'] = {
        "description": (
            "Transfer crypto -> return transaction hash and receipt URL."
        ),
        "input_model": Task25Input,
        "output_model": Task25Output,
    }

t25_inputs = [
    Task25Input(wallet_from=f"0xFROM{i}", wallet_to=f"0xTO{i}", amount=1.5 + i)
    for i in range(1, 6)
]

t25_outputs = [
    Task25Output(
        tx_hash="0xHASH",
        receipt_url="http://chain.local/tx/0xHASH",
    ) for _ in t25_inputs
]


```

</details>

