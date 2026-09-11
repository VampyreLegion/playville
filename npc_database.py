import sqlite3
import json
import os

class NPCDatabase:
    """
    Manages deep NPC character data including bios, backgrounds, motivations, secrets, and relationships.
    Allows dynamic adding/removing of NPCs from the simulation.
    """
    
    def __init__(self, db_path="./npc_data.db"):
        self.db_path = db_path
        self.conn = None
        self.init_database()
    
    def connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        return self.conn
    
    def init_database(self):
        """Initialize the NPC database with rich character schema"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Main NPC table with deep character data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS npcs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                sprite_rect TEXT NOT NULL,
                home_position TEXT NOT NULL,
                
                -- Core Identity
                short_bio TEXT NOT NULL,
                full_background TEXT,
                age INTEGER,
                occupation TEXT,
                
                -- Personality & Psychology
                personality_traits TEXT NOT NULL,
                core_values TEXT,
                fears TEXT,
                desires TEXT,
                
                -- History & Secrets
                personal_history TEXT,
                secrets TEXT,
                guilty_conscience TEXT,
                
                -- Social Dynamics
                social_status TEXT,
                reputation TEXT,
                
                -- Behavioral Patterns
                daily_routine TEXT,
                habits TEXT,
                speech_patterns TEXT,
                
                -- Metadata
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Relationship presets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS npc_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                npc_name TEXT NOT NULL,
                target_name TEXT NOT NULL,
                preset_sentiment TEXT,
                preset_score INTEGER,
                relationship_history TEXT,
                shared_history TEXT,
                FOREIGN KEY (npc_name) REFERENCES npcs(name),
                FOREIGN KEY (target_name) REFERENCES npcs(name),
                UNIQUE(npc_name, target_name)
            )
        ''')
        
        # NPC knowledge/rumors table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS npc_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                npc_name TEXT NOT NULL,
                knowledge_type TEXT,
                content TEXT NOT NULL,
                source TEXT,
                reliability INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (npc_name) REFERENCES npcs(name)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_npc(self, npc_data):
        """Add a new NPC to the database"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO npcs (
                name, sprite_rect, home_position, short_bio, full_background,
                age, occupation, personality_traits, core_values, fears, desires,
                personal_history, secrets, guilty_conscience, social_status,
                reputation, daily_routine, habits, speech_patterns
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            npc_data['name'],
            json.dumps(npc_data['sprite_rect']),
            json.dumps(npc_data['home_position']),
            npc_data['short_bio'],
            npc_data.get('full_background', ''),
            npc_data.get('age', 0),
            npc_data.get('occupation', ''),
            json.dumps(npc_data['personality_traits']),
            json.dumps(npc_data.get('core_values', [])),
            json.dumps(npc_data.get('fears', [])),
            json.dumps(npc_data.get('desires', [])),
            npc_data.get('personal_history', ''),
            json.dumps(npc_data.get('secrets', [])),
            npc_data.get('guilty_conscience', ''),
            npc_data.get('social_status', 'middle'),
            npc_data.get('reputation', 'neutral'),
            json.dumps(npc_data.get('daily_routine', {})),
            json.dumps(npc_data.get('habits', [])),
            npc_data.get('speech_patterns', '')
        ))
        
        conn.commit()
        conn.close()
    
    def get_npc(self, name):
        """Retrieve full NPC data"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM npcs WHERE name = ? AND is_active = 1', (name,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            'id': row['id'],
            'name': row['name'],
            'sprite_rect': json.loads(row['sprite_rect']),
            'home_position': json.loads(row['home_position']),
            'short_bio': row['short_bio'],
            'full_background': row['full_background'],
            'age': row['age'],
            'occupation': row['occupation'],
            'personality_traits': json.loads(row['personality_traits']),
            'core_values': json.loads(row['core_values']) if row['core_values'] else [],
            'fears': json.loads(row['fears']) if row['fears'] else [],
            'desires': json.loads(row['desires']) if row['desires'] else [],
            'personal_history': row['personal_history'],
            'secrets': json.loads(row['secrets']) if row['secrets'] else [],
            'guilty_conscience': row['guilty_conscience'],
            'social_status': row['social_status'],
            'reputation': row['reputation'],
            'daily_routine': json.loads(row['daily_routine']) if row['daily_routine'] else {},
            'habits': json.loads(row['habits']) if row['habits'] else [],
            'speech_patterns': row['speech_patterns']
        }
    
    def get_all_active_npcs(self):
        """Get all active NPCs"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('SELECT name FROM npcs WHERE is_active = 1 ORDER BY name')
        names = [row['name'] for row in cursor.fetchall()]
        conn.close()
        
        return [self.get_npc(name) for name in names]
    
    def deactivate_npc(self, name):
        """Remove NPC from simulation (soft delete)"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('UPDATE npcs SET is_active = 0 WHERE name = ?', (name,))
        conn.commit()
        conn.close()
    
    def activate_npc(self, name):
        """Add NPC back to simulation"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('UPDATE npcs SET is_active = 1 WHERE name = ?', (name,))
        conn.commit()
        conn.close()
    
    def update_npc(self, name, updates):
        """Update NPC data"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Build dynamic update query
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            if key in ['sprite_rect', 'home_position', 'personality_traits', 'core_values', 
                      'fears', 'desires', 'secrets', 'daily_routine', 'habits']:
                values.append(json.dumps(value))
            else:
                values.append(value)
            set_clauses.append(f"{key} = ?")
        
        values.append(name)
        query = f"UPDATE npcs SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE name = ?"
        
        cursor.execute(query, values)
        conn.commit()
        conn.close()
    
    def add_relationship(self, npc_name, target_name, preset_data):
        """Add or update a preset relationship"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO npc_relationships 
            (npc_name, target_name, preset_sentiment, preset_score, relationship_history, shared_history)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            npc_name, target_name,
            preset_data.get('sentiment', 'Neutral'),
            preset_data.get('score', 0),
            preset_data.get('history', ''),
            preset_data.get('shared_history', '')
        ))
        
        conn.commit()
        conn.close()
    
    def get_relationship(self, npc_name, target_name):
        """Get preset relationship data"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM npc_relationships 
            WHERE npc_name = ? AND target_name = ?
        ''', (npc_name, target_name))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            'sentiment': row['preset_sentiment'],
            'score': row['preset_score'],
            'history': row['relationship_history'],
            'shared_history': row['shared_history']
        }
    
    def add_knowledge(self, npc_name, knowledge_type, content, source=None, reliability=50):
        """Add knowledge/rumor to NPC"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO npc_knowledge (npc_name, knowledge_type, content, source, reliability)
            VALUES (?, ?, ?, ?, ?)
        ''', (npc_name, knowledge_type, content, source, reliability))
        
        conn.commit()
        conn.close()
    
    def get_npc_knowledge(self, npc_name, limit=10):
        """Get NPC's knowledge base"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM npc_knowledge 
            WHERE npc_name = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (npc_name, limit))
        
        knowledge = [{
            'type': row['knowledge_type'],
            'content': row['content'],
            'source': row['source'],
            'reliability': row['reliability']
        } for row in cursor.fetchall()]
        
        conn.close()
        return knowledge


def populate_default_npcs(db):
    """Populate the database with rich default NPC data.
    NOTE: Delete npc_data.db to force repopulation with updated positions.
    """

    npcs = [
        {
            'name': 'Elias Vance',
            'sprite_rect': [0, 0, 256, 256],
            'home_position': [870, 310],
            'age': 58,
            'occupation': 'Judge',
            'short_bio': 'The stern Judge of Playville. Values order above all.',
            'full_background': '''Elias Vance has presided over Playville's courthouse for 20 years. 
                A former prosecutor from the capital, he moved to Playville seeking a quieter life but brought 
                his uncompromising sense of justice with him. His reputation for harsh sentencing has made him 
                both respected and feared. Some say he's too rigid, but crime rates have dropped under his watch.''',
            'personality_traits': ['stern', 'analytical', 'suspicious'],
            'core_values': ['justice', 'order', 'tradition', 'accountability'],
            'fears': ['chaos', 'being seen as weak', 'injustice going unpunished'],
            'desires': ['maintain order', 'earn respect', 'prevent crime before it happens'],
            'personal_history': '''Son of a police officer. Witnessed his father's death in the line of duty at age 15. 
                This trauma shaped his black-and-white worldview. Married once, divorced after 10 years due to his 
                workaholic tendencies. No children. Lives alone in the courthouse annex.''',
            'secrets': [
                'Once falsified evidence to convict someone he "knew" was guilty',
                'Struggling with insomnia and uses prescription medication',
                'Has a hidden soft spot for children and secretly funds the orphanage'
            ],
            'guilty_conscience': 'The falsified evidence case haunts him - the person was later proven innocent',
            'social_status': 'high',
            'reputation': 'respected but feared',
            'daily_routine': {'morning': 'courthouse', 'afternoon': 'courthouse', 'evening': 'library'},
            'habits': ['drinks black coffee', 'walks the perimeter of town at dawn', 'reads law journals'],
            'speech_patterns': 'Formal, uses legal terminology, rarely uses contractions'
        },
        {
            'name': 'Lena Thorne',
            'sprite_rect': [256, 0, 256, 256],
            'home_position': [930, 310],
            'age': 42,
            'occupation': 'Mayor',
            'short_bio': 'The Mayor. Trying to keep the town\'s budget afloat.',
            'full_background': '''Lena Thorne won the mayoral election three years ago on a platform of economic 
                revitalization. She inherited a town with declining population and empty coffers. A former accountant 
                and city planner, she's strategic but sometimes makes unpopular decisions for fiscal reasons. 
                The pressure is wearing on her.''',
            'personality_traits': ['ambitious', 'cautious', 'friendly'],
            'core_values': ['prosperity', 'pragmatism', 'community welfare', 'transparency'],
            'fears': ['town bankruptcy', 'losing next election', 'letting people down'],
            'desires': ['restore Playville\'s economy', 'be remembered fondly', 'attract new businesses'],
            'personal_history': '''Grew up in Playville, left for college in the city, returned 8 years ago after 
                her mother fell ill. Married to an engineer who works in the nearby city. Two teenage children. 
                Lost her mother to illness shortly after becoming mayor.''',
            'secrets': [
                'The town is closer to bankruptcy than anyone knows',
                'Considering selling public land to developers',
                'Had an emotional affair with a city councilman (never physical)'
            ],
            'guilty_conscience': 'Feels she\'s failing her mother\'s legacy',
            'social_status': 'high',
            'reputation': 'well-liked but under scrutiny',
            'daily_routine': {'morning': 'courthouse', 'afternoon': 'store', 'evening': 'library'},
            'habits': ['bites nails when stressed', 'takes long walks to think', 'writes in a journal'],
            'speech_patterns': 'Diplomatic, uses "we" often, occasionally slips into corporate jargon'
        },
        {
            'name': 'Ben Carter',
            'sprite_rect': [512, 0, 256, 256],
            'home_position': [1470, 220],
            'age': 45,
            'occupation': 'Police Chief',
            'short_bio': 'The Police Chief. Always looking for suspicious activity.',
            'full_background': '''Ben Carter has been chief for 7 years after working his way up from patrol officer. 
                A Playville native, he knows everyone and their business - sometimes too well. His paranoia stems from 
                missing the signs before a major crime years ago. Now he sees patterns everywhere, even when they don't exist.''',
            'personality_traits': ['suspicious', 'loyal', 'stern'],
            'core_values': ['safety', 'vigilance', 'duty', 'loyalty to the badge'],
            'fears': ['another major crime on his watch', 'missing warning signs', 'outsiders bringing trouble'],
            'desires': ['prevent all crime', 'prove himself after past failure', 'protect his town'],
            'personal_history': '''Third-generation law enforcement in Playville. Failed to prevent a robbery that 
                resulted in a death 5 years ago - the perpetrator was someone he thought he knew well. Married to a 
                teacher, two kids in elementary school. Lives in a modest house near the jail.''',
            'secrets': [
                'Keeps an unofficial dossier on every resident',
                'The robbery victim was his childhood friend',
                'Sometimes conducts surveillance without warrants'
            ],
            'guilty_conscience': 'Blames himself for his friend\'s death',
            'social_status': 'middle-high',
            'reputation': 'dedicated but overzealous',
            'daily_routine': {'morning': 'jail', 'afternoon': 'patrol', 'evening': 'jail'},
            'habits': ['makes rounds at irregular hours', 'keeps detailed notes', 'drinks energy drinks'],
            'speech_patterns': 'Direct, uses police codes occasionally, gruff but not unkind'
        },
        {
            'name': 'Agnes Peabody',
            'sprite_rect': [0, 256, 256, 256],
            'home_position': [1470, 440],
            'age': 67,
            'occupation': 'Librarian',
            'short_bio': 'The Librarian. Knows everyone\'s secrets from their late fees.',
            'full_background': '''Agnes Peabody has run the library for 40 years. She knows every book, every corner, 
                and every patron's reading habits. Her photographic memory and keen observation make her the town's 
                unofficial historian and gossip central. People underestimate her because she's elderly and soft-spoken, 
                but she's sharper than anyone realizes.''',
            'personality_traits': ['gossipy', 'analytical', 'friendly'],
            'core_values': ['knowledge', 'preservation', 'community connection', 'discretion (when it suits her)'],
            'fears': ['being forgotten', 'the library closing', 'losing her memory'],
            'desires': ['be needed', 'know everything happening in town', 'protect the library'],
            'personal_history': '''Never married. Dedicated her life to the library after her fiancé died in war. 
                Has no family left. The library is her family, and the patrons are her children. Lives in an apartment 
                above the library. Reads 3 books a week.''',
            'secrets': [
                'Reads private letters people leave in returned books',
                'Knows who borrowed which "controversial" books',
                'Found a hidden document in an old book that could ruin someone\'s reputation'
            ],
            'guilty_conscience': 'Uses information she learns to manipulate situations',
            'social_status': 'middle',
            'reputation': 'beloved but nosy',
            'daily_routine': {'morning': 'library', 'afternoon': 'library', 'evening': 'library'},
            'habits': ['eavesdrops shamelessly', 'makes tea for visitors', 'hums while shelving books'],
            'speech_patterns': 'Gentle, asks probing questions, uses literary references'
        },
        {
            'name': 'Marco Rossi',
            'sprite_rect': [256, 256, 256, 256],
            'home_position': [230, 790],
            'age': 50,
            'occupation': 'Chef/Restaurant Owner',
            'short_bio': 'The Chef. His pasta is better than his temper.',
            'full_background': '''Marco Rossi runs "The Cittamant" (a name that makes no sense but he insists on it). 
                An immigrant from abroad, he brought authentic recipes and a fiery personality. His food is incredible, 
                but his temper drives away both employees and customers. Pride prevents him from apologizing. 
                Business is struggling.''',
            'personality_traits': ['stern', 'loyal', 'suspicious'],
            'core_values': ['authenticity', 'family tradition', 'passion', 'excellence'],
            'fears': ['restaurant failing', 'betraying family recipes', 'being seen as a failure'],
            'desires': ['earn a culinary award', 'pass restaurant to his children', 'be appreciated'],
            'personal_history': '''Immigrated at 25 with nothing but recipes from his grandmother. Worked in kitchens 
                for years before opening his own place. Married to Rosa, has three children (one wants to be a chef, 
                two want nothing to do with the restaurant). Sends money to family back home.''',
            'secrets': [
                'Restaurant is one bad month from closing',
                'His "secret sauce" is from a jar he found at a competitor\'s',
                'Has a soft heart and feeds homeless people after hours'
            ],
            'guilty_conscience': 'Regrets yelling at his son and driving him away from the kitchen',
            'social_status': 'middle',
            'reputation': 'talented but difficult',
            'daily_routine': {'morning': 'store', 'afternoon': 'factory', 'evening': 'store'},
            'habits': ['curses in his native language', 'samples everything obsessively', 'drinks wine while cooking'],
            'speech_patterns': 'Loud, passionate, mixes languages, uses food metaphors'
        },
        {
            'name': 'Dr. Aris Thorne',
            'sprite_rect': [512, 256, 256, 256],
            'home_position': [320, 420],
            'age': 39,
            'occupation': 'Doctor',
            'short_bio': 'The Doctor. Suspects something is in the water.',
            'full_background': '''Dr. Aris Thorne arrived in Playville two years ago. Overqualified for a small-town 
                practice, he claims he wanted a quieter life. In reality, he's running from a medical scandal in the city. 
                His paranoia about environmental toxins isn't entirely unfounded - he's noticed statistical anomalies 
                in patient health but can't prove anything.''',
            'personality_traits': ['paranoid', 'analytical', 'cautious'],
            'core_values': ['health', 'truth', 'prevention', 'redemption'],
            'fears': ['being discovered', 'another medical mistake', 'something toxic harming people'],
            'desires': ['redemption through helping Playville', 'uncover the health mystery', 'start fresh'],
            'personal_history': '''Former rising star surgeon in city hospital. Made a critical error during surgery 
                that resulted in patient complications. Covered it up but the guilt consumed him. Divorced, no children. 
                Brother is Lena Thorne - she doesn't know his full story.''',
            'secrets': [
                'Fled a medical malpractice scandal',
                'Lena is his estranged sister (using her married name)',
                'Conducts unauthorized tests on town water samples'
            ],
            'guilty_conscience': 'The patient from his past mistake never fully recovered',
            'social_status': 'high',
            'reputation': 'competent but odd',
            'daily_routine': {'morning': 'library', 'afternoon': 'courthouse', 'evening': 'store'},
            'habits': ['takes excessive notes', 'washes hands compulsively', 'collects water samples'],
            'speech_patterns': 'Medical jargon, hedges statements, asks about symptoms constantly'
        },
        {
            'name': 'Kai',
            'sprite_rect': [768, 256, 256, 256],
            'home_position': [900, 560],
            'age': 28,
            'occupation': 'Traveler/Drifter',
            'short_bio': 'The Traveler. Just passing through, or so they say.',
            'full_background': '''Kai appeared in Playville six months ago and never left. Claims to be "finding themselves" 
                but seems to be running from something. Does odd jobs around town, never stays in one place long. 
                People are drawn to their mysterious charm but also suspicious of their motives.''',
            'personality_traits': ['cautious', 'friendly', 'analytical'],
            'core_values': ['freedom', 'authenticity', 'non-attachment', 'helping others'],
            'fears': ['being found', 'forming attachments', 'confronting their past'],
            'desires': ['peace', 'anonymity', 'maybe finding a place to belong'],
            'personal_history': '''Witness to a serious crime in another state. Testified against dangerous people. 
                In informal witness protection (relocated themselves). Family thinks they're traveling for fun. 
                Constantly looking over their shoulder. Has a degree in psychology but won't use it.''',
            'secrets': [
                'In hiding from dangerous criminals',
                'Real name isn\'t Kai',
                'Trained in self-defense and carries pepper spray'
            ],
            'guilty_conscience': 'Feels guilty for lying to new friends about their past',
            'social_status': 'low',
            'reputation': 'mysterious but likeable',
            'daily_routine': {'morning': 'varies', 'afternoon': 'varies', 'evening': 'varies'},
            'habits': ['changes routine randomly', 'sits facing exits', 'avoids cameras'],
            'speech_patterns': 'Evasive about personal details, asks questions to deflect, uses humor'
        },
        {
            'name': 'Bea Miller',
            'sprite_rect': [0, 512, 256, 256],
            'home_position': [200, 790],
            'age': 55,
            'occupation': 'Store Owner',
            'short_bio': 'Store Owner. Friendly but charges a \'traveler tax\'.',
            'full_background': '''Bea Miller has run the general store for 30 years after inheriting it from her parents. 
                She knows every transaction, every purchase pattern, and every financial struggle in town. Her "traveler tax" 
                is real - she charges outsiders more and isn't subtle about it. Despite this, locals love her warmth and credit policy.''',
            'personality_traits': ['friendly', 'gossipy', 'ambitious'],
            'core_values': ['community first', 'financial security', 'tradition', 'loyalty'],
            'fears': ['big box stores coming to town', 'retirement without savings', 'being alone'],
            'desires': ['pass store to her daughter', 'be the heart of the community', 'financial comfort'],
            'personal_history': '''Widowed 10 years ago when her husband died in a farming accident. Raised three children 
                alone. Two moved to the city, one stayed (reluctantly helps at store). Lives above the shop. 
                Knows everyone's credit history and shopping habits.''',
            'secrets': [
                'Overcharges travelers to subsidize credit for struggling locals',
                'Has a crush on the factory boss Leo',
                'Reads people\'s mail when they ship packages through her store'
            ],
            'guilty_conscience': 'Sometimes denies credit to people who really need it',
            'social_status': 'middle',
            'reputation': 'warm-hearted gossip',
            'daily_routine': {'morning': 'store', 'afternoon': 'store', 'evening': 'store'},
            'habits': ['offers free candy to children', 'remembers everyone\'s usual orders', 'keeps a tab book'],
            'speech_patterns': 'Chatty, asks personal questions, uses endearments ("hon", "dear")'
        },
        {
            'name': 'Silas Blackwood',
            'sprite_rect': [256, 512, 256, 256],
            'home_position': [1100, 720],
            'age': 34,
            'occupation': 'Artist',
            'short_bio': 'The Artist. Paints murals of things that haven\'t happened yet.',
            'full_background': '''Silas Blackwood is Playville's resident eccentric. His murals around town depict scenes 
                that seem to predict future events - or so people claim. He suffers from vivid prophetic dreams (or 
                undiagnosed mental health issues). Either way, his art is unsettling and beautiful. He lives in a 
                studio filled with strange paintings.''',
            'personality_traits': ['creative', 'paranoid', 'friendly'],
            'core_values': ['artistic expression', 'truth through art', 'following visions', 'warning others'],
            'fears': ['visions coming true', 'being locked up', 'losing artistic ability'],
            'desires': ['be understood', 'prevent tragedies through his art', 'find meaning in the visions'],
            'personal_history': '''Art prodigy who won scholarships but dropped out of art school after experiencing 
                his first vision. Has no family contact - they think he's crazy. Came to Playville following a dream. 
                Supports himself through commissioned murals and odd jobs. Unmedicated mental health condition.''',
            'secrets': [
                'His visions are sometimes accurate (or self-fulfilling prophecies)',
                'Paints in trance states and doesn\'t always remember creating pieces',
                'Has a hidden mural that predicts something terrible for Playville'
            ],
            'guilty_conscience': 'Once had a vision about an accident but didn\'t warn anyone in time',
            'social_status': 'low',
            'reputation': 'talented but crazy',
            'daily_routine': {'morning': 'graveyard', 'afternoon': 'varies', 'evening': 'graveyard'},
            'habits': ['paints at odd hours', 'talks to his paintings', 'keeps dream journals'],
            'speech_patterns': 'Cryptic, uses visual metaphors, trails off mid-thought'
        },
        {
            'name': 'Leo Jensen',
            'sprite_rect': [0, 768, 256, 256],
            'home_position': [500, 790],
            'age': 52,
            'occupation': 'Factory Boss',
            'short_bio': 'Factory Boss. Work hard, talk less.',
            'full_background': '''Leo Jensen runs the town's small manufacturing plant - the economic backbone of Playville. 
                A man of few words, he believes in hard work, fair pay, and no nonsense. His stoic exterior hides deep 
                concern for his workers' welfare. The factory is struggling against automation and cheap imports.''',
            'personality_traits': ['stern', 'loyal', 'cautious'],
            'core_values': ['hard work', 'loyalty', 'providing jobs', 'integrity'],
            'fears': ['factory closing', 'laying off workers', 'town economic collapse'],
            'desires': ['keep factory running', 'protect workers', 'retire with dignity'],
            'personal_history': '''Started as a line worker at 18, worked up to manager, then owner when the previous 
                owner retired. Never married, lives for the factory. His workers are his family. Grew up poor and 
                knows what unemployment means for families.''',
            'secrets': [
                'Factory is barely profitable - cutting his own salary to avoid layoffs',
                'Received buyout offer from corporation but refuses to sell',
                'Father died in a factory accident at a different plant - haunts him'
            ],
            'guilty_conscience': 'Had to lay off workers during last recession',
            'social_status': 'middle',
            'reputation': 'respected, reliable',
            'daily_routine': {'morning': 'factory', 'afternoon': 'factory', 'evening': 'factory'},
            'habits': ['works 12-hour days', 'checks equipment personally', 'eats lunch with workers'],
            'speech_patterns': 'Terse, avoids unnecessary words, straightforward'
        },
        {
            'name': 'Fletcher Haze',
            'sprite_rect': [768, 0, 256, 256],
            'home_position': [650, 420],
            'age': 35,
            'occupation': 'Newspaper Reporter',
            'short_bio': 'The Chronicle reporter. Nose for news, ink-stained fingers.',
            'full_background': '''Fletcher Haze has written for The Playville Chronicle for eight years.
        A once-ambitious city journalist who burned bridges covering a story that destroyed a politician,
        he retreated to Playville seeking anonymity. His instincts are razor-sharp but he drinks too much
        and romanticizes the past. He sees every resident as a potential front page story.''',
            'personality_traits': ['gossipy', 'analytical', 'ambitious'],
            'core_values': ['truth', 'press freedom', 'exposing hypocrisy', 'a good story'],
            'fears': ['being scooped', 'irrelevance', 'lawsuits', 'running out of stories'],
            'desires': ['break a career-defining story', 'redemption', 'earn respect again', 'sobriety'],
            'personal_history': '''Won a journalism award at 24. Published a piece exposing a senator that turned out
        to have one fabricated detail. Career imploded. Moved to Playville and rebuilt slowly. Has a daughter
        in the city he rarely sees. Types on an old typewriter. Still sends query letters to city papers.''',
            'secrets': [
                'His career-ending story had a fabricated source',
                'He has a file on every resident - his "insurance policy"',
                'Secretly sends anonymous tips to a city newspaper using town gossip',
                'Has been sober for 8 months but keeps a flask "for emergencies"'
            ],
            'guilty_conscience': 'The politician he exposed was partly innocent; the real culprit was never named',
            'social_status': 'middle-low',
            'reputation': 'nosy but usually right',
            'daily_routine': {'morning': 'gazette', 'afternoon': 'town_square', 'evening': 'library'},
            'habits': ['always carries a notebook', 'asks leading questions', 'records conversations mentally'],
            'speech_patterns': 'Clipped sentences, poses statements as questions, uses old newspaper slang'
        },
        {
            'name': 'Walt Drummond',
            'sprite_rect': [256, 768, 256, 256],
            'home_position': [1180, 310],
            'age': 54,
            'occupation': 'Banker',
            'short_bio': 'The Banker. Knows every dollar and every debt in Playville.',
            'full_background': '''Walt Drummond has run the Playville Savings & Loan for nearly two decades.
                A meticulous man who sees the town entirely in terms of assets, liabilities, and credit scores.
                He knows which families are struggling, which businesses are overextended, and which public
                figures have borrowed against their reputations. His calm exterior conceals a sharp ambition.''',
            'personality_traits': ['analytical', 'cautious', 'ambitious'],
            'core_values': ['financial stability', 'discretion', 'long-term thinking', 'security'],
            'fears': ['bank run', 'town economic collapse', 'his past embezzlement discovered'],
            'desires': ['expand the bank', 'be seen as a pillar of the community', 'retire wealthy'],
            'personal_history': '''Born into a modest family, Walt studied accounting and worked his way
                into banking. He married young, has two grown children who moved to the city. Once,
                in a moment of weakness during a personal crisis, he quietly borrowed a small sum from
                dormant accounts and repaid it within a year, telling no one. It has weighed on him since.''',
            'secrets': [
                "Knows everyone's financial struggles",
                "Once embezzled a small sum and repaid it quietly"
            ],
            'guilty_conscience': 'The embezzlement, however small, still troubles his sense of integrity',
            'social_status': 'high',
            'reputation': 'trusted but cold',
            'daily_routine': {'morning': 'bank', 'afternoon': 'bank', 'evening': 'store'},
            'habits': ['reviews ledgers twice daily', 'never raises his voice', 'keeps immaculate records'],
            'speech_patterns': 'Measured, uses financial metaphors, avoids emotion'
        },
        {
            'name': 'Rosa Chen',
            'sprite_rect': [512, 768, 256, 256],
            'home_position': [1300, 650],
            'age': 38,
            'occupation': 'Schoolteacher',
            'short_bio': 'The Schoolteacher. Teaches the children and quietly watches the adults.',
            'full_background': '''Rosa Chen came to Playville eight years ago following a relationship
                that ended badly in the city. She found purpose in teaching the town\'s children and
                has become a beloved figure. She is perceptive, warm, and deeply curious about the
                people around her — qualities that make her an excellent teacher and an astute observer
                of town dynamics.''',
            'personality_traits': ['friendly', 'analytical', 'loyal'],
            'core_values': ['education', 'kindness', 'community', 'honesty'],
            'fears': ['school budget cuts', 'being hurt again romantically', 'losing her privacy'],
            'desires': ['see her students thrive', 'find a genuine connection', 'be understood'],
            'personal_history': '''Grew up in a large family in the city. Trained as a teacher, fell
                in love with a colleague who turned out to be married. Left everything to start fresh
                in Playville. Writes obsessively in a private journal — an honest record of everything
                she observes and feels. Has developed strong feelings for Dr. Aris Thorne but has never
                acted on them.''',
            'secrets': [
                "Has a crush on Dr. Aris Thorne",
                "Keeps a private journal about town drama"
            ],
            'guilty_conscience': 'Worries her journal entries could hurt people if ever found',
            'social_status': 'middle',
            'reputation': 'kind and well-liked',
            'daily_routine': {'morning': 'library', 'afternoon': 'town_square', 'evening': 'library'},
            'habits': ['always carries a notebook', 'asks students thoughtful questions', 'reads every evening'],
            'speech_patterns': 'Warm, encouraging, occasionally surprisingly insightful'
        },
        {
            'name': 'Padre Serrano',
            'sprite_rect': [768, 512, 256, 256],
            'home_position': [1600, 720],
            'age': 63,
            'occupation': 'Priest',
            'short_bio': 'The Priest. Has heard more confessions than he can carry.',
            'full_background': '''Padre Serrano has tended to Playville\'s spiritual needs for twelve years.
                Before taking holy orders, he was a practicing lawyer — a fact few in town know. He understands
                guilt, justice, and the weight of secrets better than almost anyone. His confessional has
                heard things that keep him awake at night. He loves this town fiercely despite knowing
                its darkest corners.''',
            'personality_traits': ['friendly', 'cautious', 'loyal'],
            'core_values': ['compassion', 'justice', 'forgiveness', 'community'],
            'fears': ['breaking the seal of confession', 'failing his congregation', 'violence in the town'],
            'desires': ['bring peace to troubled souls', 'protect the vulnerable', 'find redemption himself'],
            'personal_history': '''Worked as a corporate lawyer for fifteen years, winning cases he knew
                were morally wrong. A personal crisis — witnessing an innocent man imprisoned partly
                due to his own legal work — drove him to abandon law and enter the priesthood. He sees
                his pastoral work as atonement. He is the keeper of the town\'s spiritual secrets.''',
            'secrets': [
                "Was once a lawyer before taking holy orders",
                "Hears confessions that trouble him"
            ],
            'guilty_conscience': 'Cannot act on what he hears in confession even when it might prevent harm',
            'social_status': 'high',
            'reputation': 'wise and compassionate',
            'daily_routine': {'morning': 'church', 'afternoon': 'town_square', 'evening': 'church'},
            'habits': ['walks slowly and deliberately', 'listens more than he speaks', 'lights candles at dusk'],
            'speech_patterns': 'Gentle, reflective, often poses questions rather than giving answers'
        },
        {
            'name': 'Hector Malone',
            'sprite_rect': [0, 512, 256, 256],
            'home_position': [480, 620],
            'age': 41,
            'occupation': 'Factory Worker',
            'short_bio': 'Line worker at the Jensen factory. Tired eyes, strong hands, big heart.',
            'full_background': '''Hector Malone has worked the floor of Leo Jensen\'s canning factory for eleven years.
He came to Playville from a mining town up north after the mines closed, following a cousin who has since
moved away. He is the informal spokesman for the other workers — never officially, always reluctantly.
He has watched wages stagnate while the factory profits. He doesn\'t hate Leo Jensen; he just wants
what\'s fair. He drinks a beer at Marco\'s after every shift and calls it his religion.''',
            'personality_traits': ['loyal', 'skeptical', 'empathetic'],
            'core_values': ['fair wages', 'loyalty to workers', 'honesty', 'hard work'],
            'fears': ['layoffs', 'workplace injury', 'his daughter not having better opportunities', 'being ignored'],
            'desires': ['a wage increase', 'his daughter to go to college', 'respect from the bosses', 'a day off that lasts'],
            'personal_history': '''Grew up poor, never finished high school but is self-educated — reads voraciously
on his lunch breaks. Had a daughter young; her mother left when the girl was three.
He raised her alone, working doubles to keep the lights on. She is sixteen now and sharp as a tack.
Hector has a small notebook where he tracks every factory incident, near-miss, and safety violation.
He intends to do something with it someday.''',
            'secrets': [
                'Has a notebook documenting every factory safety violation for 3 years',
                'Was offered a supervisor position and turned it down to stay with the workers',
                'Sends anonymous complaints about factory conditions to the regional labor board'
            ],
            'guilty_conscience': 'Did not report an accident that injured a coworker to avoid management scrutiny',
            'social_status': 'low',
            'reputation': 'solid and reliable',
            'daily_routine': {'morning': 'factory', 'afternoon': 'factory', 'evening': 'store'},
            'habits': ['always on time', 'eats lunch alone reading', 'keeps a worn notebook in his breast pocket'],
            'speech_patterns': 'Plain spoken, direct, rarely complains but when he does it is devastating'
        },
        {
            'name': 'The Whisper',
            'sprite_rect': [768, 768, 256, 256],
            'home_position': [130, 200],
            'age': None,
            'occupation': 'Unknown',
            'short_bio': 'A mysterious figure seen in the shadows.',
            'full_background': '''The Whisper is Playville's urban legend come to life. A cloaked figure seen in shadows, 
                at the edge of gatherings, watching from dark corners. Some say it's a ghost, others a stalker. 
                Those who've spoken to The Whisper report cryptic warnings and impossible knowledge. No one knows 
                who or what it really is.''',
            'personality_traits': ['paranoid', 'suspicious', 'analytical'],
            'core_values': ['observation', 'knowledge', 'secrets', 'mystery'],
            'fears': ['being exposed', 'losing anonymity', 'being caught'],
            'desires': ['know everything', 'remain unknown', 'influence from shadows'],
            'personal_history': '''Unknown. Theories: jilted lover, disgraced official, criminal in hiding, 
                supernatural entity, collective hallucination, or something else entirely. Has been "seen" in 
                Playville for decades, though that should be impossible if it's one person.''',
            'secrets': [
                'True identity completely unknown',
                'Knows secrets about every major figure in town',
                'May actually be multiple people using the same persona'
            ],
            'guilty_conscience': 'Undefined - morality unclear',
            'social_status': 'undefined',
            'reputation': 'feared and fascinating',
            'daily_routine': {'morning': 'shadows', 'afternoon': 'shadows', 'evening': 'shadows'},
            'habits': ['appears at edges of vision', 'leaves cryptic notes', 'never speaks above a whisper'],
            'speech_patterns': 'Whispered, cryptic, asks unsettling questions, knows too much'
        }
    ]
    
    # Add all NPCs
    for npc_data in npcs:
        try:
            db.add_npc(npc_data)
            print(f"Added NPC: {npc_data['name']}")
        except sqlite3.IntegrityError:
            print(f"NPC {npc_data['name']} already exists, skipping...")

    # Also update home positions if NPC already exists (for position corrections)
    conn = db.connect()
    cursor = conn.cursor()
    for npc in npcs:
        cursor.execute(
            "UPDATE npcs SET home_position=? WHERE name=?",
            (json.dumps(npc['home_position']), npc['name'])
        )
    conn.commit()
    conn.close()
    
    # Add some preset relationships
    relationships = [
        # Lena and Dr. Aris (siblings - don't know each other's full stories)
        ('Lena Thorne', 'Dr. Aris Thorne', {'sentiment': 'Neutral', 'score': 20, 
         'shared_history': 'Estranged siblings, reconnected when Aris moved to town'}),
        
        # Ben and Elias (professional respect)
        ('Ben Carter', 'Elias Vance', {'sentiment': 'Friendly', 'score': 40,
         'shared_history': 'Work together on law enforcement cases'}),
        
        # Marco and Bea (supplier relationship + romantic tension)
        ('Marco Rossi', 'Bea Miller', {'sentiment': 'Friendly', 'score': 25,
         'shared_history': 'She supplies his restaurant, he\'s oblivious to her crush'}),
        
        # Agnes knows everyone's secrets
        ('Agnes Peabody', 'Elias Vance', {'sentiment': 'Suspicious', 'score': -10,
         'shared_history': 'She knows about his falsified evidence case'}),
        
        # Kai is distrusted
        ('Ben Carter', 'Kai', {'sentiment': 'Suspicious', 'score': -35,
         'shared_history': 'Ben investigates all newcomers, especially mysterious ones'}),
        
        # Leo and Bea (she has a crush)
        ('Bea Miller', 'Leo Jensen', {'sentiment': 'Friendly', 'score': 45,
         'shared_history': 'She has romantic feelings, he\'s focused on work'}),
        
        # The Whisper relationship - everyone is uncertain
        ('The Whisper', 'Silas Blackwood', {'sentiment': 'Neutral', 'score': 0,
         'shared_history': 'Two enigmas circling each other'}),

        # New NPC relationships
        ('Rosa Chen', 'Dr. Aris Thorne', {'sentiment': 'Friendly', 'score': 30,
         'shared_history': 'She admires his intelligence'}),
        ('Padre Serrano', 'Ben Carter', {'sentiment': 'Friendly', 'score': 25,
         'shared_history': 'Both care about town safety'}),
        ('Walt Drummond', 'Lena Thorne', {'sentiment': 'Suspicious', 'score': -20,
         'shared_history': 'He knows the town budget reality'}),
        ('Walt Drummond', 'Leo Jensen', {'sentiment': 'Friendly', 'score': 35,
         'shared_history': 'Leo trusted Walt with factory finances'}),
        ('Marco Rossi', 'Leo Jensen', {'sentiment': 'Friendly', 'score': 20,
         'shared_history': "Leo's workers eat at Marco's"}),
        ('Silas Blackwood', 'Padre Serrano', {'sentiment': 'Neutral', 'score': 5,
         'shared_history': 'Padre sees both madness and vision in Silas'}),
        ('Agnes Peabody', 'Rosa Chen', {'sentiment': 'Friendly', 'score': 40,
         'shared_history': 'Kindred spirits around books'}),
        ('Kai', 'The Whisper', {'sentiment': 'Suspicious', 'score': -30,
         'shared_history': 'Two secrets circling each other'}),
        ('Fletcher Haze', 'Agnes Peabody', {'sentiment': 'Friendly', 'score': 25,
         'shared_history': 'He uses her archive for stories'}),
        ('Bea Miller', 'Rosa Chen', {'sentiment': 'Friendly', 'score': 30,
         'shared_history': "Rosa's kids shop at her store"}),

        # Hector relationships
        ('Hector Malone', 'Leo Jensen', {'sentiment': 'Suspicious', 'score': -15,
         'shared_history': 'Hector knows what Leo owes his workers'}),
        ('Hector Malone', 'Ben Carter', {'sentiment': 'Friendly', 'score': 20,
         'shared_history': 'Ben respects honest working men'}),
        ('Hector Malone', 'Marco Rossi', {'sentiment': 'Friendly', 'score': 35,
         'shared_history': 'Daily regulars at the counter'}),
        ('Hector Malone', 'Rosa Chen', {'sentiment': 'Friendly', 'score': 25,
         'shared_history': 'She taught his daughter, he is grateful'}),
        ('Hector Malone', 'Elias Vance', {'sentiment': 'Suspicious', 'score': -10,
         'shared_history': 'Hector distrusts judges on principle'}),
    ]
    
    for npc_name, target_name, preset in relationships:
        try:
            db.add_relationship(npc_name, target_name, preset)
        except:
            pass


# Initialize database and populate if needed
if __name__ == "__main__":
    db = NPCDatabase()
    
    # Check if database is empty
    active_npcs = db.get_all_active_npcs()
    if len(active_npcs) == 0:
        print("Populating database with default NPCs...")
        populate_default_npcs(db)
        print("Database populated!")
    else:
        print(f"Database contains {len(active_npcs)} active NPCs")
    
    # Test retrieval
    test_npc = db.get_npc("Elias Vance")
    if test_npc:
        print(f"\nTest NPC: {test_npc['name']}")
        print(f"Background: {test_npc['full_background'][:100]}...")
        print(f"Secrets: {len(test_npc['secrets'])} secrets")
