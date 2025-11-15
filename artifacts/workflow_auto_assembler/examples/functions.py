from typing import Type, List
from pydantic import BaseModel, Field

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

class SummarizeTextInput(BaseModel):
    content: str = Field(..., description="Text to summarize.")

class SummarizeTextOutput(BaseModel):
    summary: str = Field(..., description="Short summarized version of the content.")

def summarize_text(inputs: SummarizeTextInput) -> SummarizeTextOutput:
    """Summarize long content."""
    return SummarizeTextOutput(summary="Short summary...")

class DetectSentimentInput(BaseModel):
    text: str

class DetectSentimentOutput(BaseModel):
    sentiment: str
    score: float

def detect_sentiment(inputs: DetectSentimentInput) -> DetectSentimentOutput:
    """Detect sentiment of given text."""
    return DetectSentimentOutput(sentiment="positive", score=0.9)


class ExtractKeywordsInput(BaseModel):
    text: str

class ExtractKeywordsOutput(BaseModel):
    keywords: List[str]

def extract_keywords(inputs: ExtractKeywordsInput) -> ExtractKeywordsOutput:
    """Extract keywords."""
    return ExtractKeywordsOutput(keywords=["keyword1", "keyword2"])


class ConvertUnitsInput(BaseModel):
    value: float
    from_unit: str
    to_unit: str

class ConvertUnitsOutput(BaseModel):
    converted_value: float

def convert_units(inputs: ConvertUnitsInput) -> ConvertUnitsOutput:
    """Convert measurement units."""
    return ConvertUnitsOutput(converted_value=inputs.value * 1.3)


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


class GeneratePlotInput(BaseModel):
    data: List[float]
    title: str

class GeneratePlotOutput(BaseModel):
    image_path: str

def generate_plot(inputs: GeneratePlotInput) -> GeneratePlotOutput:
    """Generate plot."""
    return GeneratePlotOutput(image_path="/tmp/plot.png")

class CurrencyExchangeInput(BaseModel):
    amount: float
    from_currency: str
    to_currency: str

class CurrencyExchangeOutput(BaseModel):
    converted_amount: float

def currency_exchange(inputs: CurrencyExchangeInput) -> CurrencyExchangeOutput:
    """Convert currencies."""
    return CurrencyExchangeOutput(converted_amount=inputs.amount * 1.1)

class StoreFileInput(BaseModel):
    filename: str
    content: str

class StoreFileOutput(BaseModel):
    storage_path: str

def store_file(inputs: StoreFileInput) -> StoreFileOutput:
    """Store file."""
    return StoreFileOutput(storage_path=f"/tmp/{inputs.filename}")


class LoadFileInput(BaseModel):
    path: str

class LoadFileOutput(BaseModel):
    content: str

def load_file(inputs: LoadFileInput) -> LoadFileOutput:
    """Load file from storage."""
    return LoadFileOutput(content="Loaded file contents...")


class SendSMSInput(BaseModel):
    phone: str
    message: str

class SendSMSOutput(BaseModel):
    success: bool

def send_sms(inputs: SendSMSInput) -> SendSMSOutput:
    """Send SMS."""
    return SendSMSOutput(success=True)

class DetectObjectsInput(BaseModel):
    image_path: str

class DetectObjectsOutput(BaseModel):
    objects: List[str]

def detect_objects(inputs: DetectObjectsInput) -> DetectObjectsOutput:
    """Detect objects in image."""
    return DetectObjectsOutput(objects=["cat", "chair"])

class TranscribeAudioInput(BaseModel):
    audio_path: str

class TranscribeAudioOutput(BaseModel):
    text: str

def transcribe_audio(inputs: TranscribeAudioInput) -> TranscribeAudioOutput:
    """Transcribe audio file."""
    return TranscribeAudioOutput(text="Transcribed text")

class GenerateReportInput(BaseModel):
    title: str
    body: str

class GenerateReportOutput(BaseModel):
    pdf_path: str

def generate_report(inputs: GenerateReportInput) -> GenerateReportOutput:
    """Generate report."""
    return GenerateReportOutput(pdf_path="/tmp/report.pdf")

class LookupCoordinatesInput(BaseModel):
    city: str

class LookupCoordinatesOutput(BaseModel):
    lat: float
    lon: float

def lookup_coordinates(inputs: LookupCoordinatesInput) -> LookupCoordinatesOutput:
    """Lookup coordinates."""
    return LookupCoordinatesOutput(lat=10.0, lon=20.0)

class CheckAvailabilityInput(BaseModel):
    item_id: str
    location: str

class CheckAvailabilityOutput(BaseModel):
    available: bool
    stock: int

def check_availability(inputs: CheckAvailabilityInput) -> CheckAvailabilityOutput:
    """Check stock."""
    return CheckAvailabilityOutput(available=True, stock=5)

class CreateOrderInput(BaseModel):
    item_id: str
    quantity: int

class CreateOrderOutput(BaseModel):
    order_id: str
    status: str

def create_order(inputs: CreateOrderInput) -> CreateOrderOutput:
    """Create order."""
    return CreateOrderOutput(order_id="ORD-001", status="created")


class CheckOrderStatusInput(BaseModel):
    order_id: str

class CheckOrderStatusOutput(BaseModel):
    status: str

def check_order_status(inputs: CheckOrderStatusInput) -> CheckOrderStatusOutput:
    """Check order status."""
    return CheckOrderStatusOutput(status="in progress")

class UploadImageInput(BaseModel):
    image_path: str
    label: str

class UploadImageOutput(BaseModel):
    success: bool
    url: str

def upload_image(inputs: UploadImageInput) -> UploadImageOutput:
    """Upload image."""
    return UploadImageOutput(success=True, url="http://img.local")


class RewriteTextInput(BaseModel):
    text: str
    tone: str

class RewriteTextOutput(BaseModel):
    rewritten: str

def rewrite_text(inputs: RewriteTextInput) -> RewriteTextOutput:
    """Rewrite text in specified tone."""
    return RewriteTextOutput(rewritten=f"{inputs.tone} version of {inputs.text}")

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

class QueryWebInput(BaseModel):
    search_input: str = Field(..., description="Topic to be searched on the web.")


class QueryWebOutput(BaseModel):
    search_results: List[str] = Field(..., description="List relevant info from search results.")


def query_web(inputs : QueryWebInput) -> QueryWebOutput:
    """Get information from the internet for provided query."""
    return QueryWebOutput(
        search_results = ["Relevant content found in first search result is ..."],
    )
