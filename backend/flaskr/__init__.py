from flask import Flask, request, abort, jsonify
from flask_cors import CORS
import random
import math

from models import setup_db, Question, Category, db

QUESTIONS_PER_PAGE = 10

def paginate_questions(request, selection):
    page = request.args.get('page', 1, type=int)
    start = (page - 1) * QUESTIONS_PER_PAGE
    end = start + QUESTIONS_PER_PAGE

    max_page = math.ceil(len(selection) / QUESTIONS_PER_PAGE)
    if page > max_page:
        abort(404)

    questions = [question.format() for question in selection]
    current_questions = questions[start:end]
    return current_questions


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)

    if test_config is None:
        setup_db(app)
    else:
        database_path = test_config.get('SQLALCHEMY_DATABASE_URI')
        setup_db(app, database_path=database_path)

    """
    @TODO: Set up CORS. Allow '*' for origins. Delete the sample route after completing the TODOs
    """
    cors = CORS(app, resources={r"/*": {"origins": "*"}})

    with app.app_context():
        db.create_all()

    """
    @TODO: Use the after_request decorator to set Access-Control-Allow
    """
    @app.after_request
    def after_request(response):
        
        if not response.headers.get('Access-Control-Allow-Origin'):
            response.headers.add('Access-Control-Allow-Origin', '*')  
    
        if not response.headers.get('Access-Control-Allow-Headers'):
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,true')
    
        if not response.headers.get('Access-Control-Allow-Methods'):
            response.headers.add('Access-Control-Allow-Methods', 'GET,PATCH,POST,DELETE,OPTIONS')

        return response

    """
    @TODO:
    Create an endpoint to handle GET requests
    for all available categories.
    """
    @app.route('/categories', methods=['GET'])
    def get_categories():
        categories = Category.query.all()
        
        formatted_categories = {category.id: category.type for category in categories}

        return jsonify({
            'categories': formatted_categories
        })


    """
    @TODO:
    Create an endpoint to handle GET requests for questions,
    including pagination (every 10 questions).
    This endpoint should return a list of questions,
    number of total questions, current category, categories.

    TEST: At this point, when you start the application
    you should see questions and categories generated,
    ten questions per page and pagination at the bottom of the screen for three pages.
    Clicking on the page numbers should update the questions.
    """
    @app.route('/questions', methods=['GET'])
    def get_questions():
        selection = Question.query.order_by(Question.id).all()
        total_questions = len(selection)

        current_questions = paginate_questions(request, selection)

        categories = Category.query.all()
        formatted_categories = {category.id: category.type for category in categories}

        current_category = "ALL"
        if len(selection) > 0:
            current_category = selection[0].category

        return jsonify({
            'questions': current_questions,
            'totalQuestions': total_questions,
            'categories': formatted_categories,
            'currentCategory': current_category
        })

    """
    @TODO:
    Create an endpoint to DELETE question using a question ID.

    TEST: When you click the trash icon next to a question, the question will be removed.
    This removal will persist in the database and when you refresh the page.
    """
    @app.route('/questions/<int:id>', methods=['DELETE'])
    def delete_question(id):
        question = Question.query.get(id)  
        if question is None:
            abort(404)
        
        try:
            question.delete()  
            return jsonify({'deleted': id}), 200
        
        except:
            abort(422)



    """
    @TODO:
    Create an endpoint to POST a new question,
    which will require the question and answer text,
    category, and difficulty score.

    TEST: When you submit a question on the "Add" tab,
    the form will clear and the question will appear at the end of the last page
    of the questions list in the "List" tab.
    """

    """
    @TODO:
    Create a POST endpoint to get questions based on a search term.
    It should return any questions for whom the search term
    is a substring of the question.

    TEST: Search by any phrase. The questions list will update to include
    only question that include that string within their question.
    Try using the word "title" to start.
    """
    @app.route('/questions', methods=['POST'])
    def post_questions():
        body = request.get_json()

        # POST route for SEARCH questions
        if 'searchTerm' in body:
            search_term = body.get('searchTerm', '')
            selection = Question.query.filter(Question.question.ilike(f'%{search_term}%')).all()
            questions = [question.format() for question in selection]
            
            total_questions = len(selection)
            current_category = "ALL"
            if len(selection) > 0:
                current_category = selection[0].category

            return jsonify({
                'questions': questions,
                'totalQuestions': total_questions,
                'currentCategory': current_category
            })
        
        # POST route to CREATE new questions
        else:
            question = body.get('question', None)
            answer = body.get('answer', None)
            difficulty = body.get('difficulty', None)
            category_id = body.get('category', None)

            if not all([question, answer, difficulty, category_id]):
                abort(400)
            
            # Searching for the CATEGORY TYPE to Create the New Question
            category = Category.query.get(category_id)
            if category is None:
                abort(404)

            try:    
                new_question = Question(question=question, answer=answer, difficulty=difficulty, category=category.type)
                new_question.insert()
                return jsonify({
                    'success': True
                })
            
            except:
                db.session.rollback()
                abort(500)


    """
    @TODO:
    Create a GET endpoint to get questions based on category.

    TEST: In the "List" tab / main screen, clicking on one of the
    categories in the left column will cause only questions of that
    category to be shown.
    """
    @app.route('/categories/<int:id>/questions', methods=['GET'])
    def get_questions_by_category(id):

        category = Category.query.get(id)  
        if category is None:
            abort(404) 

        selection = Question.query.filter(Question.category == category.type).order_by(Question.id).all()  
        total_questions = len(selection)  
        current_questions = paginate_questions(request, selection) 

        return jsonify({
            'questions': current_questions,
            'totalQuestions': total_questions,
            'currentCategory': category.type  
        })

    """
    @TODO:
    Create a POST endpoint to get questions to play the quiz.
    This endpoint should take category and previous question parameters
    and return a random questions within the given category,
    if provided, and that is not one of the previous questions.

    TEST: In the "Play" tab, after a user selects "All" or a category,
    one question at a time is displayed, the user is allowed to answer
    and shown whether they were correct or not.
    """
    @app.route('/quizzes', methods=['POST'])
    def post_quizzes():
        body = request.get_json()
        previous_questions = body.get('previous_questions', [])
        quiz_category = body.get('quiz_category', None)
        if quiz_category is None:
            return jsonify({'message': 'category is required'}), 400
        
        category_id = quiz_category.get('id')
        if category_id is None:
            return jsonify({'message': 'category is not found'}), 404
        
        # if Category is 'ALL':
        if category_id == 0:
            questions = Question.query.filter(Question.id.notin_(previous_questions)).all()
        # if Category is a specific one
        else:
            try:
                category = Category.query.get(category_id)

                if category is None:
                    abort(404)
                
                questions = Question.query.filter(Question.category==category.type,
                                                  Question.id.notin_(previous_questions)).all()
                
            except:
                return jsonify({'message': 'Category not found'}), 404
        
        # When there are no more questions:
        if not questions:
            return jsonify({'question': None}), 200
        # Otherwise keep playing
        question = random.choice(questions)

        return jsonify({'question': question.format()}), 200

    """
    @TODO:
    Create error handlers for all expected errors
    including 404 and 422.
    """
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 400,
            'message': 'bad request'
        }), 400
    
    @app.errorhandler(404)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 404,
            'message': 'resource not found'
        }), 404

    @app.errorhandler(405)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 405,
            'message': 'method not allowed'
        }), 405

    @app.errorhandler(422)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 422,
            'message': 'unprocessable'
        }), 422

    @app.errorhandler(500)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 500,
            'message': 'internal server error'
        }), 500


    return app

