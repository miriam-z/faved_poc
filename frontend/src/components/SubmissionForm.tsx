'use client'

import { useState, useEffect } from 'react'
import {
  FormContainer,
  Form,
  FormGroup,
  Label,
  Input,
  TextArea,
  Button,
  Select,
  ErrorMessage,
  EvaluationResults,
  ResultsTitle,
  Decision,
  SummarySection,
  SummaryTitle,
  SummaryText,
  QuestionList,
  QuestionItem,
  QuestionText,
  FeedbackItem,
  FeedbackLabel,
  LoadingOverlay,
  LoadingSpinner,
  LoadingText,
  ErrorContainer,
  ErrorTitle,
  ErrorDetails,
  LeftColumn,
  ResultsContainer,
} from './styles'
import styled from 'styled-components'

type SubmissionType = 'text' | 'image' | 'video'

interface SubmissionResponse {
  evaluation: {
    questions: Array<{
      question: string
      corrections: string
      what_went_well: string
    }>
    summary: {
      corrections: string
      what_went_well: string
      decision: 'ACCEPT' | 'REJECT'
    }
  }
}

const FileInput = styled.input`
  display: none;
`;

const FileLabel = styled.label`
  display: inline-block;
  padding: 10px 20px;
  background-color: #ccc; /* Gray color */
  color: white;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s;
  width: 100%; /* Match width to submit button */
  text-align: center;

  &:hover {
    background-color: #bbb; /* Slightly darker gray on hover */
  }
`;

export default function SubmissionForm() {
  const [type, setType] = useState<SubmissionType>('text')
  const [text, setText] = useState('')
  const [imageUrl, setImageUrl] = useState('')
  const [videoUrl, setVideoUrl] = useState('')
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [fileName, setFileName] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [errorDetails, setErrorDetails] = useState('')
  const [response, setResponse] = useState<SubmissionResponse | null>(null)

  const resetForm = () => {
    setText('')
    setImageUrl('')
    setVideoUrl('')
    setVideoFile(null)
    setFileName('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setErrorDetails('')

    try {
      let endpoint = ''
      const formData = new FormData()

      switch (type) {
        case 'text':
          endpoint = 'http://localhost:8000/text'
          formData.append('text', text)
          break
        case 'image':
          endpoint = 'http://localhost:8000/image'
          formData.append('image_url', imageUrl)
          break
        case 'video':
          endpoint = 'http://localhost:8000/video'
          if (videoFile) {
            formData.append('file', videoFile)
          }
          break
      }

      console.log('Sending request to:', endpoint)

      const res = await fetch(endpoint, {
        method: 'POST',
        body: formData,
      })

      const data = await res.json()

      if (!res.ok) {
        console.error('Error response:', data)
        throw new Error(data.detail || 'Failed to evaluate submission')
      }

      if (!data || !data.evaluation) {
        console.error('Invalid response format:', data)
        throw new Error('Invalid response format from server')
      }

      console.log('Success response:', data)
      setResponse(data)
    } catch (err) {
      console.error('Error:', err)
      setError(err instanceof Error ? err.message : 'An unexpected error occurred')
      if (err instanceof Error) {
        setErrorDetails(err.stack || '')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newType = e.target.value as SubmissionType
    setType(newType)
    setError('')
    setErrorDetails('')
    resetForm()
  }

  const getLoadingMessage = () => {
    const textMessages = [
      "Analyzing your words with AI magic... ✨",
      "Reading between the lines... 📝",
      "Consulting with the digital experts... 🤖",
      "Brewing up some insights... ☕️",
      "Making your content shine... ✨",
    ]

    const imageMessages = [
      "Analyzing your masterpiece... 🎨",
      "Looking at every pixel... 🔍",
      "Finding the visual story... 📸",
      "Decoding your creative vision... 🎯",
      "Extracting the visual magic... ✨",
    ]

    const videoMessages = [
      "Watching your video with AI eyes... 👀",
      "Analyzing every frame... 🎬",
      "Finding the perfect moments... 🎥",
      "Processing your creative genius... 🌟",
      "Extracting video insights... 📊",
    ]

    // Get random message based on type
    const messages = type === 'text'
      ? textMessages
      : type === 'image'
        ? imageMessages
        : videoMessages

    const randomIndex = Math.floor(Math.random() * messages.length)
    return messages[randomIndex]
  }

  // Add state for cycling through messages
  const [loadingMessage, setLoadingMessage] = useState('')

  // Update useEffect to cycle through messages
  useEffect(() => {
    if (loading) {
      const interval = setInterval(() => {
        setLoadingMessage(getLoadingMessage())
      }, 2000) // Change message every 2 seconds

      setLoadingMessage(getLoadingMessage()) // Set initial message
      return () => clearInterval(interval)
    }
  }, [loading, type])

  return (
    <FormContainer>
      {loading && (
        <LoadingOverlay>
          <LoadingSpinner />
          <LoadingText>{loadingMessage}</LoadingText>
        </LoadingOverlay>
      )}

      <LeftColumn>
        <Form onSubmit={handleSubmit}>
          <FormGroup>
            <Label htmlFor="type">Submission Type</Label>
            <Select
              id="type"
              value={type}
              onChange={handleTypeChange}
            >
              <option value="text">Text</option>
              <option value="image">Image URL</option>
              <option value="video">Video File</option>
            </Select>
          </FormGroup>

          {type === 'text' && (
            <FormGroup>
              <Label htmlFor="text">Text Content</Label>
              <TextArea
                id="text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Enter your text submission..."
                required
              />
            </FormGroup>
          )}

          {type === 'image' && (
            <FormGroup>
              <Label htmlFor="imageUrl">Image URL</Label>
              <Input
                id="imageUrl"
                type="url"
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
                placeholder="Enter image URL..."
                required
              />
            </FormGroup>
          )}

          {type === 'video' && (
            <FormGroup>
              <Label htmlFor="videoFile">Video File</Label>
              <FileInput
                id="videoFile"
                type="file"
                accept=".mp4, .mp3, .mov"
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    setVideoFile(e.target.files[0]);
                    setFileName(e.target.files[0].name);
                  }
                }}
              />
              <FileLabel htmlFor="videoFile">Choose File</FileLabel>
              {fileName && <span>{fileName}</span>}
            </FormGroup>
          )}

          <Button type="submit" disabled={loading}>
            {loading ? 'Evaluating...' : 'Submit for Evaluation'}
          </Button>

          {error && (
            <ErrorContainer>
              <ErrorTitle>Error</ErrorTitle>
              <ErrorMessage>{error}</ErrorMessage>
              {errorDetails && <ErrorDetails>{errorDetails}</ErrorDetails>}
            </ErrorContainer>
          )}
        </Form>

        {response && (
          <ResultsContainer>
            <ResultsTitle>Evaluation Results</ResultsTitle>
            <Decision decision={response.evaluation.summary.decision}>
              {response.evaluation.summary.decision}
            </Decision>
            <SummarySection>
              <SummaryTitle>Summary</SummaryTitle>
              <FeedbackItem>
                <FeedbackLabel>Corrections:</FeedbackLabel>
                <SummaryText>{response.evaluation.summary.corrections}</SummaryText>
              </FeedbackItem>
              <FeedbackItem>
                <FeedbackLabel>What went well:</FeedbackLabel>
                <SummaryText>{response.evaluation.summary.what_went_well}</SummaryText>
              </FeedbackItem>
            </SummarySection>
          </ResultsContainer>
        )}
      </LeftColumn>

      {response && (
        <EvaluationResults>
          <QuestionList>
            {response.evaluation.questions.map((q, index) => (
              <QuestionItem key={index}>
                <QuestionText>{q.question}</QuestionText>
                <FeedbackItem>
                  <FeedbackLabel>Corrections:</FeedbackLabel>
                  <SummaryText>{q.corrections}</SummaryText>
                </FeedbackItem>
                <FeedbackItem>
                  <FeedbackLabel>What went well:</FeedbackLabel>
                  <SummaryText>{q.what_went_well}</SummaryText>
                </FeedbackItem>
              </QuestionItem>
            ))}
          </QuestionList>
        </EvaluationResults>
      )}
    </FormContainer>
  )
} 