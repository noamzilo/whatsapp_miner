# Message Classification Package

This package contains the message classification functionality for the WhatsApp Miner.

## Overview

The message classification system automatically analyzes WhatsApp messages to identify potential leads for local services. It uses Groq's LLM API with LangChain for structured output parsing.

## Components

### MessageClassifier

The main class that handles:
- Querying unclassified messages from the database
- Classifying messages using Groq LLM API
- Creating classification records in the database
- Creating lead records for classified leads
- Marking messages as processed

### ClassificationResult

A Pydantic model that defines the structured output format for LLM classification:
- `is_lead`: Boolean indicating if the message represents a lead
- `lead_category`: Category of the lead (e.g., 'dentist', 'spanish_classes')
- `lead_description`: Description of what the person is looking for
- `confidence_score`: Confidence score between 0 and 1
- `reasoning`: Explanation for the classification

## Configuration

### Environment Variables

- `MESSAGE_CLASSIFIER_RUN_EVERY_SECONDS`: How often to run the classifier (default: 30)
- `GROQ_API_KEY`: API key for Groq LLM service

### Database Tables

The system uses the following database tables:
- `whatsapp_messages`: Messages to be classified
- `message_intent_classifications`: Classification results
- `detected_leads`: Lead records for classified leads
- `lead_classification_prompts`: LLM prompts for classification
- `lead_categories`: Categories for different types of leads
- `message_intent_types`: Types of message intents

## Usage

### Running the Classifier

```bash
python src/message_classification/classify_new_messages.py
```

### Manual Testing

There are two manual test files for different purposes:

#### Basic Model Test (No Environment Variables Required)
```bash
python src/message_classification/manual_test_basic.py
```
This test verifies the ClassificationResult Pydantic model works correctly without requiring any environment variables or database connection.

#### Full Classifier Test (Requires Environment Variables)
```bash
# First set up environment variables
export GROQ_API_KEY="your_groq_api_key_here"
export SUPABASE_DATABASE_CONNECTION_STRING="your_db_connection_string"

# Then run the test
python src/message_classification/manual_test_classifier.py
```
This test verifies the full MessageClassifier works with Groq API and database integration.

## Features

1. **Continuous Processing**: Runs in a loop, checking for new messages every X seconds
2. **Structured Output**: Uses LangChain and Pydantic for reliable JSON parsing
3. **Error Handling**: Graceful error handling with logging
4. **Database Integration**: Full integration with existing database schema
5. **Configurable**: Easy to configure via environment variables
6. **Lead Creation**: Automatically creates lead records for classified leads

## LLM Prompt

The system uses a configurable prompt stored in the database:

```
You are a classifier for WhatsApp messages from local groups. Your task is to determine if a message represents someone looking for a local service.

Services can include: dentist, spanish classes, restaurants, tutors, plumbers, electricians, and any other local business or service.

Analyze the message and respond with a JSON object containing:
- is_lead: boolean indicating if this is a lead
- lead_category: string describing the category (if it's a lead)
- lead_description: string describing what they're looking for (if it's a lead)
- confidence_score: float between 0 and 1
- reasoning: string explaining your classification

Message: {message_text}
```

## Deployment

The classifier is deployed as a separate Docker container with its own entrypoint script. The deployment configuration is in:
- `entrypoint_message_classifier.sh`: Entrypoint script
- `Dockerfile`: Docker configuration
- `.github/workflows/deploy.yml`: GitHub Actions deployment 