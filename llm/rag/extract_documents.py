from typing import Any


def extract_documents(knowledge: list):
    documentation = []
    for section in knowledge:
        
        type = section["type"]

        match type:
            case "workExperience":
                documentation.extend(extract_workExperience(section))
            case "clientEngagement":
                documentation.extend(extract_clientEngagement(section))
            case "certifications":
                documentation.extend(extract_certifications(section))
            case "education":
                documentation.extend(extract_education(section))
            case "project":
                documentation.extend(extract_project(section))
            case "contact":
                documentation.extend(extract_contact(section))
            case "technical_skills":
                documentation.extend(extract_skills(section))
            case "professional_profile":
                documentation.extend(extract_summary(section))
            case _:
                print(f"Warning: unsupported section type: {type}")
    return documentation

def extract_workExperience(section):
    documents = []

    text = "Company: " + section["id"]
    text += "\n\tTitle: " + section["title"]
    
    # Summary
    text += "\n\nSummary:"
    for summary in section.get("summary", []):
        text += "\n\t" + summary
    
    # Responsibilities
    text += "\n\nResponsibilities:"
    for respon in section.get("coreResponsibilities", []):
        text += "\n\t" + respon
    
    # CloudPlatforms
    text += "\n\nCloudPlatforms:"
    for cloud in section.get("cloudPlatforms", []):
        text += "\n\t" + cloud

    # RelatedSkill
    text += "\n\nRelatedSkills:"
    for skill in section.get("relatedSkills", []):
        text += "\n\t" + skill.replace("skill-", "")
    
    # Clients
    text += "\n\nClients: "
    for client in section.get("clients", []):
        text += "\n\t" + client

    # Keywords
    text += "\n\nKeywords"
    metadata = section.get("retrievalMetadata", {})
    for keyword in metadata.get("keywords", []):
        text += "\n\t" + keyword
    
    # Embedding Text
    text += "\n\nEmbedding Text:\n"
    text += metadata.get("embeddingText", "")

    # print(text)
    documents.append(text)
    return documents
    

def extract_clientEngagement(section):
    documents = []

    id = "Company: " + section.get("id", "")
    text = id 

    # Summary
    text += "\n\nSummary:"
    for summary_text in section.get("summary", []):
        text += "\n" + summary_text

    # Responsibilities
    text += "\n\nResponsibilities: "
    for responsibilities in section.get("responsibilities", []):
        text += "\n\t" + responsibilities

    # Achievements
    for achievement in section.get("achievements", []):
        text += "Title: " + achievement.get("title", "")
        text += "\nStatement: " + achievement.get("statement", "")
        
        skills = achievement.get("skills", [])

        if skills:
            text += "\nSkills: "

            for skill in achievement.get("skills", []):
                text += "\n\t" + skill

        text += "\n" + achievement.get("embeddingText", "")

    documents.append(text)
    return documents

def extract_skills(section):
    documents = []

    for category in section.get("categories", []):
        lines = []

        lines.append(f"Category: {category.get('name', '')}")

        for skill in category.get("skills", []):
            line = f"- {skill.get('name', '')}"

            proficiency = skill.get("proficiency")
            if proficiency:
                line += f" ({proficiency})"

            lines.append(line)

        documents.append("\n".join(lines))

    return documents

def extract_certifications(section: dict[str, Any]) -> list[str]:
    documents: list[str] = []

    for cert in section.get("certifications", []):
        lines: list[str] = []

        name = cert.get("name", "")
        if name:
            lines.append(f"Certification: {name}")

        vendor = cert.get("vendor", "")
        if vendor:
            lines.append(f"Vendor: {vendor}")

        category = cert.get("category", "")
        if category:
            lines.append(f"Category: {category}")

        level = cert.get("level", "")
        if level:
            lines.append(f"Level: {level}")

        status = cert.get("status", "")
        if status:
            lines.append(f"Status: {status}")

        skills = cert.get("skills", [])
        if skills:
            lines.append(f"Skills: {', '.join(skills)}")

        target_roles = cert.get("targetRoles", [])
        if target_roles:
            lines.append(f"Target Roles: {', '.join(target_roles)}")

        embedding_text = cert.get("embeddingText", "")
        if embedding_text:
            lines.append(f"Embedding Text: {embedding_text}")

        text = "\n".join(lines).strip()

        if text:
            documents.append(text)

    return documents

def extract_project(project):
    documents = []
    text = f"Project: {project.get('title', '')}"

    if project.get("summary"):
        text += f"\n\nSummary:\n{project['summary']}"
        for summary in project.get("summary"):
            text += summary

    if project.get("problem", ""):
        text += "\n\nProglem: " + project.get("problem", "")

    if project.get("solution", ""):
        text += "\n\nSolution: " + project.get("solution", "")


    if project.get("architecture", ""):
        arch = project.get("architecture")
        text += "\n\nArchitecture:"

        # Cloud
        if arch.get("cloud", []):
            text += "\n\tCloud: "
            for cloud in arch.get("cloud"):
                text += "\n\t\t" + cloud
                # Cloud
        if arch.get("languages", []):
            text += "\n\tLanguages: "
            for languages in arch.get("languages"):
                text += "\n\t\t" + languages
        if arch.get("models", []):
            text += "\n\tAWS AI Services: "
            for model in arch.get("models"):
                text += "\n\t\t" + model
        if arch.get("dataStores", []):
            text += "\n\tDataStores: "
            for dataStores in arch.get("dataStores"):
                text += "\n\t\t" + dataStores
        if arch.get("components", []):
            text += "\n\tComponents: "
            for components in arch.get("components"):
                text += "\n\t\t" + components
        
    skills = project.get("relatedSkills", [])
    if skills:
        text += "\n\nRelated Skills:"
        for skill in skills:
            text += "\n\t" + skill.replace("skill-", "")

    if project.get("github"):
        text += f"\n\nGitHub:\n{project['github']}"

    if project.get("portfolio"):
        text += f"\nPortfolio:\n{project['portfolio']}"

    if project.get("businessImpact", []):
        text += "\n\nBusiness Impact: "
        for businessImpact in project.get("businessImpact", []):
            text += "\n\t" + businessImpact

    metadata = project.get("retrievalMetadata", {})
    if metadata.get("keywords"):
        text += "\n\nKeywords:"
        for keyword in metadata["keywords"]:
            text += "\n\t" + keyword

    if metadata.get("embeddingText"):
        text += "\n\nEmbedding Text:\n"
        text += metadata["embeddingText"]

    documents.append(text)
    return documents

def extract_education(education):
    documents = []

    education = education.get("education", [])

    if education:
        for school in education:
            text = f"School: {school.get('id', '')}"

            if school.get("degree"):
                text += f"\nDegree: {school['degree']}"

            if school.get("major"):
                text += f"\nMajor: {school['major']}"

            if school.get("graduationYear"):
                text += f"\nGraduated: {school['graduationYear']}"
            
            relatedDisciplines = school.get("relatedDisciplines", []) 
            if relatedDisciplines:
                text += "\n\nRelated Disciplines:"
                for relatedDiscipline in relatedDisciplines:
                    text += "\n\t" + relatedDiscipline

            if school.get("embeddingText"):
                text += "\n\nEmbedding Text:\n"
                text += school["embeddingText"]

    documents.append(text)
    return documents


def extract_summary(summary):
    documents = []
    text = "Professional Summary\n\n"

    for line in summary.get("statements", []):
        text += line + "\n"

    if summary.get("embeddingText"):
        text += "\nEmbedding Text:\n"
        text += summary["embeddingText"]

    documents.append(text)
    return documents

def extract_contact(contact):
    documents = []
    text = ""

    if contact.get("name"):
        text += f"Name: {contact['name']}\n"

    if contact.get("location"):
        text += f"Location: {contact['location']}\n"

    if contact.get("linkedin"):
        text += f"LinkedIn: {contact['linkedin']}\n"

    if contact.get("portfolio"):
        text += f"Portfolio: {contact['portfolio']}\n"

    documents.append(text)
    return documents