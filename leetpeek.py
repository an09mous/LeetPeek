import requests, json, os, time, argparse, shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

endpoint = 'https://leetcode.com/graphql'

parser = argparse.ArgumentParser(description="Arguments for leetcode interview experience crawler")
parser.add_argument(
    "--company", 
    type=str, 
    default="tessell", 
    help="Company name in lowercase for which you want to get the interview experiences"
)

parser.add_argument(
    "--thresh", 
    type=int, 
    default=500, 
    help="Skip all the interview experiences if they are less than this threshold value. Default is 500"
)

args = parser.parse_args()

company = args.company
interview_min_char_length = args.thresh
company_dir = f"articles/{company}"
metadata_file_path = f"{company_dir}/metadata.json"

# Defining the graphql queries
LIST_QUERY = '''query discussPostItems($orderBy: ArticleOrderByEnum, $keywords: [String]!, $tagSlugs: [String!], $skip: Int, $first: Int) {
  ugcArticleDiscussionArticles(
    orderBy: $orderBy
    keywords: $keywords
    tagSlugs: $tagSlugs
    skip: $skip
    first: $first
  ) {
    totalNum
    pageInfo {
      hasNextPage
    }
    edges {
      node {
        uuid
        title
        slug
        summary
        author {
          realName
          userAvatar
          userSlug
          userName
          nameColor
          certificationLevel
          activeBadge {
            icon
            displayName
          }
        }
        isOwner
        isAnonymous
        isSerialized
        scoreInfo {
          scoreCoefficient
        }
        articleType
        thumbnail
        summary
        createdAt
        updatedAt
        status
        isLeetcode
        canSee
        canEdit
        isMyFavorite
        myReactionType
        topicId
        hitCount
        reactions {
          count
          reactionType
        }
        tags {
          name
          slug
          tagType
        }
        topic {
          id
          topLevelCommentCount
        }
      }
    }
  }
}
    ,
   '''

ARTICLE_QUERY = '''query discussPostDetail($topicId: ID!) {
  ugcArticleDiscussionArticle(topicId: $topicId) {
    uuid
    title
    slug
    summary
    content
    author {
      realName
      userAvatar
      userSlug
      userName
      nameColor
      certificationLevel
      activeBadge {
        icon
        displayName

            }

        }
    isOwner
    isAnonymous
    isSerialized
    isAuthorArticleReviewer
    scoreInfo {
      scoreCoefficient

        }
    articleType
    thumbnail
    summary
    createdAt
    updatedAt
    status
    isLeetcode
    canSee
    canEdit
    isMyFavorite
    myReactionType
    topicId
    hitCount
    reactions {
      count
      reactionType

        }
    tags {
      name
      slug
      tagType

        }
    topic {
      id
      topLevelCommentCount

        }

    }

}
    '''

# Helper functions

def save_to_file(filepath: str, content: str):
    with open(filepath, "w", encoding="utf-8") as file:
        file.write(content)

def ensure_directory_exists(directory):
    Path(directory).mkdir(parents=True, exist_ok=True)

def file_exists(filepath):
    return Path(filepath).is_file()

def delete_directory(dir_path):
    if os.path.exists(dir_path) and os.path.isdir(dir_path):  # Check if directory exists
        shutil.rmtree(dir_path)

def decorate_content(article, content : str):
    return f"[{article['title']}](https://leetcode.com/discuss/post/{article['topicId']}) | {article['updatedAt']} \n\n" + content

def filter_content(content: str):
    return content.replace('\\n', '\n')

def run_graphql_query(endpoint_url, query, variables=None, headers=None, retries = 3):
    """
    Execute a GraphQL query against the specified endpoint
    
    Args:
        endpoint_url (str): The URL of the GraphQL endpoint
        query (str): The GraphQL query or mutation
        variables (dict, optional): Variables for the GraphQL query
        headers (dict, optional): HTTP headers to include in the request
        
    Returns:
        dict: The JSON response from the GraphQL server
    """
    # Default headers if none provided
    if headers is None:
        headers = {
            'Content-Type': 'application/json',
        }
    
    # Construct the payload
    payload = {
        'query': query
    }
    
    # Add variables if provided
    if variables:
        payload['variables'] = variables
    
    # Make the request
    response = requests.post(
        endpoint_url,
        data=json.dumps(payload),
        headers=headers
    )
    
    # Check for HTTP errors
    if response.status_code != 200 and retries > 0:
        return run_graphql_query(endpoint_url, query, variables, headers, retries - 1)
    response.raise_for_status()
    
    # Return the JSON response
    return response.json()

def update_metadata(last_article_updated_at):
    data = {
        "lastArticleUpdatedAt": last_article_updated_at
    }

    save_to_file(metadata_file_path, json.dumps(data))

    
def get_and_save_article(article, article_id):
    try:
        resp = run_graphql_query(endpoint, ARTICLE_QUERY, {"topicId": str(article["topicId"])})
    except Exception as e:
        print(f"Couldn't get article with exception - {e}")
        return
    content = resp["data"]["ugcArticleDiscussionArticle"]["content"]
    if len(content) < interview_min_char_length:
        return
    content = filter_content(content)
    content = decorate_content(article, content)

    ensure_directory_exists(company_dir)
    save_to_file(f"{company_dir}/article_{article_id}.md", content)

# Crawler function
def crawl(last_article_updated_at = None):
    has_next_page = True
    max_pages = 100
    batch_no = 0
    page_size = 200
    skip = 0
    latest_article_updated_at = last_article_updated_at
    total_start_time = time.time()
    while has_next_page and max_pages:
        variables = {
            "orderBy": "MOST_RECENT",
            "keywords": [
                company
            ],
            "tagSlugs": [
                "interview"
            ],
            "skip": skip,
            "first": page_size
        }
        max_pages = max_pages - 1
        skip = skip + page_size
        
        try:
            resp = run_graphql_query(endpoint, LIST_QUERY, variables)
        except Exception as e:
            print(f"Couldn't get articles in batch {batch_no} with exception - {e}")
            continue

        has_next_page = resp["data"]["ugcArticleDiscussionArticles"]["pageInfo"]["hasNextPage"]
        articles = resp["data"]["ugcArticleDiscussionArticles"]["edges"]
        with ThreadPoolExecutor(max_workers=8 * os.cpu_count()) as executor:
                start_time = time.time()
                futures = []
                for article in articles:
                    article_node = article["node"]
                    if company not in article_node["title"].lower():
                        continue

                    article_updated_at = article_node["updatedAt"]
                    if (last_article_updated_at and article_updated_at <= last_article_updated_at):
                        has_next_page = False
                        break

                    if latest_article_updated_at == last_article_updated_at:
                        latest_article_updated_at = article_updated_at

                    futures.append(executor.submit(get_and_save_article, article_node, article_updated_at))

                for future in as_completed(futures):
                    future.result()
                    
                end_time = time.time()
                print(f"Batch {batch_no} completed in time: {end_time-start_time}")
        batch_no = batch_no + 1

    if last_article_updated_at != latest_article_updated_at:
        update_metadata(latest_article_updated_at)
    total_end_time = time.time()
    print(f"Process completed in time: {total_end_time-total_start_time}")

def main():
    # Getting the timestamp after which to crawl the articles from the metadata file for the company if exists
    last_article_updated_at = None
    if file_exists(metadata_file_path):
        with open(metadata_file_path, "r", encoding="utf-8") as file:
            last_article_updated_at = json.load(file)["lastArticleUpdatedAt"]
    else:
        delete_directory(company_dir)

    crawl(last_article_updated_at)


if __name__ == '__main__':
    main()