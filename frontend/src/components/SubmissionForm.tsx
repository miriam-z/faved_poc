'use client'

import { useState } from 'react'
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
  SuccessMessage,
} from './styles'

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

export default function SubmissionForm() {
  const [type, setType] = useState<SubmissionType>('text')
  const [text, setText] = useState('')
  const [imageUrl, setImageUrl] = useState('')
  const [videoUrl, setVideoUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [response, setResponse] = useState<SubmissionResponse | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setResponse(null)

    try {
      let endpoint = ''
      let payload = {}

      switch (type) {
        case 'text':
          endpoint = 'http://localhost:8000/text'
          payload = { text }
          break
        case 'image':
          endpoint = 'http://localhost:8000/image'
          payload = { image_url: imageUrl }
          break
        case 'video':
          endpoint = 'http://localhost:8000/video'
          payload = { youtube_url: videoUrl }
          break
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        const error = await res.json()
        throw new Error(error.detail || 'Failed to evaluate submission')
      }

      const data = await res.json()
      setResponse(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <FormContainer>
      <Form onSubmit={handleSubmit}>
        <FormGroup>
          <Label htmlFor="type">Submission Type</Label>
          <Select
            id="type"
            value={type}
            onChange={(e) => setType(e.target.value as SubmissionType)}
          >
            <option value="text">Text</option>
            <option value="image">Image URL</option>
            <option value="video">YouTube Video</option>
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
            <Label htmlFor="videoUrl">YouTube URL</Label>
            <Input
              id="videoUrl"
              type="url"
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              placeholder="Enter YouTube video URL..."
              required
            />
          </FormGroup>
        )}

        <Button type="submit" disabled={loading}>
          {loading ? 'Evaluating...' : 'Submit for Evaluation'}
        </Button>

        {error && <ErrorMessage>{error}</ErrorMessage>}

        {response && (
          <SuccessMessage>
            <h3>Evaluation Results:</h3>
            <p>Decision: {response.evaluation.summary.decision}</p>
            <p>Corrections: {response.evaluation.summary.corrections}</p>
            <p>What went well: {response.evaluation.summary.what_went_well}</p>
          </SuccessMessage>
        )}
      </Form>
    </FormContainer>
  )
} 