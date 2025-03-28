'use client'

import SubmissionForm from '@/components/SubmissionForm'
import styled from 'styled-components'

const Container = styled.main`
  min-height: 100vh;
  padding: 2rem;
  background-color: #f5f5f5;
`

const Header = styled.header`
  text-align: center;
  margin-bottom: 2rem;
`

const Title = styled.h1`
  font-size: 2rem;
  color: #333;
  margin-bottom: 1rem;
`

const Description = styled.p`
  color: #666;
  max-width: 600px;
  margin: 0 auto;
`

export default function Home() {
  return (
    <Container>
      <Header>
        <Title>Influencer Submission Evaluator</Title>
        <Description>
          Submit your content for evaluation. We support text, image URLs, and YouTube video links.
        </Description>
      </Header>
      <SubmissionForm />
    </Container>
  )
}
